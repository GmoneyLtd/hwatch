import asyncio
import hashlib
import json
import os
import random
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from core.batch_writer import batch_save_result
from core.collector import run_task
from core.config_loader import AppConfig, DeviceConfig, TaskConfig
from core.database import save_result
from core.error_handler import error_handler
from core.file_buffer import get_file_buffer

# from core.performance_monitor import performance_monitor
from core.string_optimizer import get_template_cache


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

        # Check if the task is still enabled in the current configuration
        # This prevents race conditions where a job starts just as the configuration is reloaded and the task is disabled.
        try:
            current_task_config = next(t for t in self.config.tasks if t.alias == task.alias)
            if not current_task_config.enabled:
                logger.info(f"Task {task.alias} has been disabled, skipping execution of job {job_id}.")
                return  # Stop execution if disabled
        except StopIteration:
            logger.info(f"Task {task.alias} has been removed, skipping execution of job {job_id}.")
            return  # Stop execution if removed

        # Use the most up-to-date task configuration for the execution
        task = current_task_config

        # Record task start time
        start_time = datetime.now()
        logger.info(f"Starting job execution: {job_id}")

        task_success = False
        results = None

        # Performance monitoring
        # performance_monitor.increment_counter("task_executions")

        # async with performance_monitor.measure_time("task_execution", {"task": task.alias, "device": device.name}):
        try:
            # Run collection task
            results = await run_task(task, device)

            if results is None:
                logger.warning(
                    f"Job {job_id} returned no results (possibly disabled, execution failed, or match failed)."
                )
                task_success = False
                # performance_monitor.increment_counter("failed_tasks")
            else:
                task_success = True
                # performance_monitor.increment_counter("successful_tasks")

                # Process results based on storage strategy
                if task.storage == "sqlite":
                    # Use batch writer for better performance
                    # async with performance_monitor.measure_time("database_save"):
                    # 使用任务开始时间作为数据采集时间戳
                    await batch_save_result(
                        task.alias, device.name, {k: v for k, v in results.items() if k != "raw_output"}, start_time
                    )
                elif task.storage == "file":
                    # Use optimized file writing
                    # async with performance_monitor.measure_time("file_save"):
                    outfile_dir = "outfile"
                    file_path = os.path.join(outfile_dir, f"{task.alias}_{device.name}.log")

                    # Use template cache for efficient string formatting
                    template_cache = get_template_cache()
                    end_time = datetime.now()
                    content = template_cache.format_file_content(task, device, results, start_time, end_time)

                    # Use async file buffer for better I/O performance
                    file_buffer = get_file_buffer()
                    await file_buffer.write_buffered(file_path, content)
                    logger.debug(f"Job {job_id} results buffered to {file_path}")

        except asyncio.CancelledError:
            # Handle graceful shutdown - don't log as error since it's expected
            logger.debug(f"Job {job_id} was cancelled during shutdown")
            # performance_monitor.increment_counter("cancelled_tasks")
            # Don't re-raise the exception to avoid APScheduler error logs
            return  # Early return for cancellation, no rescheduling
        except Exception as e:
            # Enhanced error handling with classification and recovery
            should_retry = await error_handler.handle_error(
                exception=e,
                device=device.name,
                task=task.alias,
                context={"job_id": job_id, "start_time": start_time},
            )

            if should_retry:
                logger.info(f"Job {job_id} will be retried based on error analysis")
                # performance_monitor.increment_counter("retried_tasks")
            else:
                logger.error(f"Job {job_id} execution failed permanently: {e}")
                # performance_monitor.increment_counter("permanently_failed_tasks")

            task_success = False
            # Don't re-raise the exception to prevent APScheduler from logging it again

        # Handle execution frequency and rescheduling logic (regardless of success/failure)
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
            status_msg = "successful" if task_success else "failed"
            logger.info(f"Job {job_id} (delay mode) {status_msg}, scheduled next run at {next_run_time}")

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
        if task.protocol == "ssh" and task.ssh:
            task_data["ssh"] = {"command": task.ssh.command}
            if task.ssh.parse:
                task_data["ssh"]["parse"] = {
                    "regex": task.ssh.parse.regex,
                    "calculate": task.ssh.parse.calculate,
                }
        elif task.protocol == "snmp" and task.snmp:
            task_data["snmp"] = {"oid": task.snmp.oid, "type": task.snmp.type}
            if task.snmp.parse:
                task_data["snmp"]["parse"] = {
                    "regex": task.snmp.parse.regex,
                    "calculate": task.snmp.parse.calculate,
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

    def _calculate_start_delay(self, schedule) -> float:
        """Calculate random start delay to prevent thundering herd effect

        Args:
            schedule: Task schedule configuration

        Returns:
            Random delay in seconds (0 to reasonable maximum)
        """
        if schedule.frequency == 1:
            # Single execution: small random delay (0-10s)
            return random.uniform(0, 10)

        elif schedule.mode == "interval" and schedule.seconds:
            # Interval mode: delay within 0 to min(interval * 3, 60s)
            max_delay = min(schedule.seconds * 3, 60)
            return random.uniform(0, max_delay)

        elif schedule.mode == "delay" and schedule.seconds:
            # Delay mode: delay within 0 to min(delay_time, 60s)
            max_delay = min(schedule.seconds, 60)
            return random.uniform(0, max_delay)

        else:
            # Default: small random delay
            return random.uniform(0, 5)

    def schedule_task_for_device(self, task: TaskConfig, device: DeviceConfig):
        """Schedule task for specific device with staggered start time"""
        job_id = f"{task.alias}_{device.name}"
        schedule = task.schedule

        # If task already exists, remove it first
        self.remove_job(job_id)

        # If task is disabled, don't schedule
        if not task.enabled:
            logger.info(f"Task {task.alias} is disabled, will not schedule job")
            return

        # Calculate staggered start time to avoid thundering herd
        start_delay = self._calculate_start_delay(schedule)
        start_time = datetime.now() + timedelta(seconds=start_delay)

        # Schedule new job
        if schedule.frequency == 1:
            self.scheduler.add_job(
                self._execute_job,
                "date",
                run_date=start_time,
                args=[task, device],
                id=job_id,
            )
            logger.info(f"Scheduled job {job_id} (execute once, start_delay in {start_delay:.1f}s).")
        elif schedule.mode == "interval" and schedule.seconds is not None:
            self.scheduler.add_job(
                self._execute_job,
                IntervalTrigger(seconds=schedule.seconds),
                args=[task, device],
                id=job_id,
                next_run_time=start_time,  # Set first execution time
            )
            logger.info(f"Scheduled job {job_id} (interval {schedule.seconds}s, start_delay in {start_delay:.1f}s).")
        elif schedule.mode == "delay":
            # First execution in delay mode with random delay
            self.scheduler.add_job(
                self._execute_job,
                "date",
                run_date=start_time,
                args=[task, device],
                id=job_id,
            )
            logger.info(f"Scheduled job {job_id} (delay mode, start_delay in {start_delay:.1f}s).")
