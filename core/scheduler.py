import asyncio
import hashlib
import json
import os
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from core.collector import run_task
from core.config_loader import AppConfig, DeviceConfig, TaskConfig
from core.database import save_result


class TaskScheduler:
    def __init__(self, config: AppConfig):
        self.scheduler = AsyncIOScheduler()
        self.config = config
        self.device_map = {device.name: device for device in config.devices}
        self.job_counts: dict[str, int] = {}
        self.task_signatures: dict[str, str] = {}  # Store task signatures for comparison

    async def _execute_job(self, task: TaskConfig, device: DeviceConfig):
        """Wrapper function for actually executing a single job."""
        job_id = f"{task.alias}_{device.name}"
        # Record task start time
        start_time = datetime.now()
        logger.info(f"Starting job execution: {job_id}")

        try:
            # Run collection task
            results = await run_task(task, device)

            if results is None:
                logger.warning(
                    f"Job {job_id} returned no results (possibly disabled, execution failed, or match failed)."
                )
                return

            # Process results based on storage strategy
            if task.storage == "sqlite":
                await save_result(task.alias, device.name, {k: v for k, v in results.items() if k != "raw_output"})
            elif task.storage == "file":
                outfile_dir = "outfile"
                os.makedirs(outfile_dir, exist_ok=True)
                # Use task alias and device name combination as filename, append mode
                file_path = os.path.join(outfile_dir, f"{task.alias}_{device.name}.log")

                # Build complete file content
                start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                end_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

                # Build task information header
                header_lines = [
                    f"=================== {start_time_str} ===================",
                    f"Task: {task.alias}",
                    f"Device: {device.name} ({device.ip})",
                    f"Protocol: {task.protocol}",
                    f"Type: {task.type}",
                ]

                # Add protocol-specific parameters
                if task.protocol == "ssh" and task.command:
                    header_lines.append(f"Command: {str(task.command)}")
                elif task.protocol == "snmp" and task.oid:
                    header_lines.append(f"OID: {task.oid}")

                # Build result content
                result_lines = ["Results:"]
                if "raw_output" in results:
                    result_lines.append(results["raw_output"])
                else:
                    for key, value in results.items():
                        result_lines.append(f"{key}: {value}")

                # Build end marker
                footer_lines = [
                    "",  # Empty line separator
                    f"+------------------ {end_time_str} ------------------+",
                    "",
                    "",
                    "",
                ]

                # Merge all content and write to file
                all_content = "\n".join(header_lines + result_lines + footer_lines)
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(all_content)
                logger.info(f"Job {job_id} results have been appended to {file_path}")

            # Handle execution frequency and 'delay' mode rescheduling
            self.job_counts[job_id] = self.job_counts.get(job_id, 0) + 1

            schedule = task.schedule
            # If execution count limit exists and reached, stop
            if schedule.frequency > 0 and self.job_counts[job_id] >= schedule.frequency:
                logger.info(
                    f"Job {job_id} has reached its execution frequency {schedule.frequency} times, will no longer be scheduled."
                )
                return

            # If in delay mode, need to manually schedule next execution here
            if schedule.mode == "delay" and schedule.seconds is not None:
                next_run_time = datetime.now() + timedelta(seconds=schedule.seconds)
                self.scheduler.add_job(
                    self._execute_job,
                    "date",
                    run_date=next_run_time,
                    args=[task, device],
                    id=f"{job_id}_adhoc_{self.job_counts[job_id]}",
                )
                logger.info(f"Job {job_id} (delay mode) has scheduled next run at {next_run_time}")

        except asyncio.CancelledError:
            # Handle graceful shutdown - don't log as error since it's expected
            logger.debug(f"Job {job_id} was cancelled during shutdown")
            # Don't re-raise the exception to avoid APScheduler error logs
        except Exception as e:
            logger.error(f"Job {job_id} execution failed: {e}")
            # Don't re-raise the exception to prevent APScheduler from logging it again

    def schedule_all_tasks(self):
        """Schedule all enabled tasks according to current configuration."""
        self.scheduler.remove_all_jobs()
        self.job_counts.clear()
        self.task_signatures.clear()
        logger.info("Clearing existing jobs, starting to reschedule according to new configuration...")

        for task in self.config.tasks:
            # Generate and save task signature
            self.task_signatures[task.alias] = self.get_task_signature(task)

            if not task.enabled:
                continue

            self._schedule_single_task(task, self.device_map)

    def get_task_signature(self, task: TaskConfig) -> str:
        """Generate task signature for change comparison"""
        # Create key attributes dictionary for task
        task_data = {
            "alias": task.alias,
            "enabled": task.enabled,
            "protocol": task.protocol,
            "targets": sorted(task.targets),  # Sort to ensure consistency
            "storage": task.storage,
            "schedule": {
                "frequency": task.schedule.frequency,
                "mode": task.schedule.mode,
                "seconds": task.schedule.seconds,
            },
        }

        # Add protocol-specific attributes
        if task.protocol == "ssh":
            task_data["command"] = task.command
        elif task.protocol == "snmp":
            task_data["type"] = task.type
            task_data["oid"] = task.oid

        # Add parsing configuration
        if task.parse:
            task_data["parse"] = {
                "regex": task.parse.regex,
                "calculate": task.parse.calculate,
            }

        if task.labels:
            task_data["labels"] = task.labels

        # Generate MD5 signature
        task_json = json.dumps(task_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(task_json.encode("utf-8")).hexdigest()

    def compare_configs(self, new_config: AppConfig) -> dict:
        """Compare new and old configurations, return change information"""
        changes = {
            "added": [],  # Newly added tasks
            "removed": [],  # Deleted tasks
            "modified": [],  # Modified tasks
            "unchanged": [],  # Unchanged tasks
        }

        # Build task mapping and signatures for new configuration
        new_tasks = {task.alias: task for task in new_config.tasks}
        new_signatures = {alias: self.get_task_signature(task) for alias, task in new_tasks.items()}

        # Build task mapping for old configuration
        old_tasks = {task.alias: task for task in self.config.tasks}

        # Check each new task
        for alias, _ in new_tasks.items():
            if alias not in old_tasks:
                changes["added"].append(alias)
            elif new_signatures[alias] != self.task_signatures.get(alias):
                changes["modified"].append(alias)
            else:
                changes["unchanged"].append(alias)

        # Check deleted tasks
        for alias in old_tasks:
            if alias not in new_tasks:
                changes["removed"].append(alias)

        return changes

    def update_tasks_incrementally(self, new_config: AppConfig):
        """Incrementally update task scheduling"""
        logger.info("Starting incremental task scheduling update...")

        # Compare configuration changes
        changes = self.compare_configs(new_config)

        # Update device mapping
        new_device_map = {device.name: device for device in new_config.devices}

        # Record change statistics
        total_changes = len(changes["added"]) + len(changes["removed"]) + len(changes["modified"])
        if total_changes == 0:
            logger.info("No configuration changes, skipping task scheduling update")
            return

        logger.info(
            f"Configuration changes detected: added {len(changes['added'])}, removed {len(changes['removed'])}, modified {len(changes['modified'])}, unchanged {len(changes['unchanged'])}"
        )

        # Handle deleted tasks
        for alias in changes["removed"]:
            self._remove_task_jobs(alias)
            if alias in self.task_signatures:
                del self.task_signatures[alias]
            logger.info(f"Deleted task: {alias}")

        # Handle modified tasks
        for alias in changes["modified"]:
            self._remove_task_jobs(alias)
            task = next(t for t in new_config.tasks if t.alias == alias)
            self._schedule_single_task(task, new_device_map)
            self.task_signatures[alias] = self.get_task_signature(task)
            logger.info(f"Updated task: {alias}")

        # Handle newly added tasks
        for alias in changes["added"]:
            task = next(t for t in new_config.tasks if t.alias == alias)
            self._schedule_single_task(task, new_device_map)
            self.task_signatures[alias] = self.get_task_signature(task)
            logger.info(f"Added task: {alias}")

        # Update configuration and device mapping
        self.config = new_config
        self.device_map = new_device_map

        logger.success(f"Incremental update completed! Processed {total_changes} changes")

    def _remove_task_jobs(self, task_alias: str):
        """Remove all jobs for specified task"""
        jobs_to_remove = []
        for job in self.scheduler.get_jobs():
            if job.id.startswith(f"{task_alias}_"):
                jobs_to_remove.append(job.id)

        for job_id in jobs_to_remove:
            self.remove_job(job_id)
            # Clean up job count
            if job_id in self.job_counts:
                del self.job_counts[job_id]

    def _schedule_single_task(self, task: TaskConfig, device_map: dict[str, DeviceConfig]):
        """Schedule a single task"""
        if not task.enabled:
            logger.info(f"Task {task.alias} is disabled, skipping scheduling")
            return

        for device_name in task.targets:
            device = device_map.get(device_name)
            if not device:
                logger.warning(
                    f"Target device {device_name} for task {task.alias} is not defined in configuration, skipped"
                )
                continue

            self.schedule_task_for_device(task, device)

    def reload_config_and_update_tasks(self, new_config: AppConfig):
        """Reload configuration and incrementally update tasks"""
        if new_config:
            self.update_tasks_incrementally(new_config)
        else:
            logger.error("New configuration is empty, keeping current scheduling unchanged")

    def start(self):
        logger.info("Starting scheduler...")
        self.scheduler.start()

    def stop(self, wait_timeout: int = 30):
        """Gracefully shutdown scheduler with timeout

        Args:
            wait_timeout: Maximum seconds to wait for running jobs to complete
        """
        logger.info(f"Shutting down scheduler (waiting up to {wait_timeout}s for running jobs)...")

        # Get count of running jobs before shutdown
        running_jobs = len(self.scheduler.get_jobs())
        if running_jobs > 0:
            logger.info(f"Waiting for {running_jobs} running jobs to complete...")

        try:
            # Shutdown with wait parameter - this will wait for running jobs to complete
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler shutdown completed successfully")
        except Exception as e:
            logger.warning(f"Error during scheduler shutdown: {e}")
            # Force shutdown if graceful shutdown fails
            try:
                self.scheduler.shutdown(wait=False)
                logger.info("Forced scheduler shutdown completed")
            except Exception as force_e:
                logger.error(f"Failed to force shutdown scheduler: {force_e}")

    def remove_job(self, job_id: str):
        """Remove specified job from scheduler"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job {job_id} from scheduler")
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id} from scheduler: {e}")

    def schedule_task_for_device(self, task: TaskConfig, device: DeviceConfig):
        """Schedule task for specific device"""
        job_id = f"{task.alias}_{device.name}"
        schedule = task.schedule

        # If task already exists, remove it first
        self.remove_job(job_id)

        # If task is disabled, don't schedule
        if not task.enabled:
            logger.info(f"Task {task.alias} is disabled, will not schedule job")
            return

        # Schedule new job
        if schedule.frequency == 1:
            self.scheduler.add_job(
                self._execute_job,
                "date",
                run_date=datetime.now() + timedelta(seconds=1),
                args=[task, device],
                id=job_id,
            )
            logger.info(f"Scheduled job {job_id} (execute once only).")
        elif schedule.mode == "interval" and schedule.seconds is not None:
            self.scheduler.add_job(
                self._execute_job, IntervalTrigger(seconds=schedule.seconds), args=[task, device], id=job_id
            )
            logger.info(f"Scheduled job {job_id} (interval mode, every {schedule.seconds} seconds).")
        elif schedule.mode == "delay":
            # First execution in delay mode is immediate
            self.scheduler.add_job(
                self._execute_job,
                "date",
                run_date=datetime.now() + timedelta(seconds=1),
                args=[task, device],
                id=job_id,
            )
            logger.info(f"Scheduled job {job_id} (delay mode, first execution).")
