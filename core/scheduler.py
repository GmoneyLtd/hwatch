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
        self.task_signatures: dict[str, str] = {}  # 存储任务签名用于对比

    async def _execute_job(self, task: TaskConfig, device: DeviceConfig):
        """实际执行单个作业的包装函数。"""
        job_id = f"{task.alias}_{device.name}"
        logger.info(f"开始执行作业: {job_id}")

        # 运行采集任务
        results = await run_task(task, device)

        if results is None:
            logger.warning(f"作业 {job_id} 未返回结果 (可能被禁用、执行失败或匹配失败)。")
            return

        # 根据存储策略处理结果
        if task.storage == "sqlite":
            await save_result(task.alias, device.name, {k: v for k, v in results.items() if k != "raw_output"})
        elif task.storage == "file":
            outfile_dir = "outfile"
            os.makedirs(outfile_dir, exist_ok=True)
            # 使用任务别名和设备名的组合作为文件名, 追加模式
            file_path = os.path.join(outfile_dir, f"{task.alias}_{device.name}.log")

            # 准备写入内容, 包含时间戳和任务信息
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            content_lines = [
                f"=================== {timestamp} ===================",
                f"Task: {task.alias}",
                f"Device: {device.name} ({device.ip})",
                f"Protocol: {task.protocol}",
                f"Type: {task.type}",
            ]

            # 添加具体的任务参数
            if task.protocol == "ssh" and task.command:
                content_lines.append(f"Command: {str(task.command)}")
            elif task.protocol == "snmp" and task.oid:
                content_lines.append(f"OID: {task.oid}")

            content_lines.append("Results:\n")

            # 添加结果内容
            if "raw_output" in results:
                content_lines.append(results["raw_output"])
            else:
                # 如果有解析后的结果,也显示
                for key, value in results.items():
                    content_lines.append(f"{key}: {value}")

            content_lines.append("")  # 空行分隔

            # 追加写入文件
            with open(file_path, "a", encoding="utf-8") as f:
                f.write("\n".join(content_lines))
                # 添加分隔符: 空行 + 分隔线 + 空行
                f.write("\n" + "+" + "-" * 57 + "+" + "\n\n\n")
            logger.info(f"作业 {job_id} 的结果已追加到 {file_path}")

        # 处理执行频率和 'delay' 模式的重调度
        self.job_counts[job_id] = self.job_counts.get(job_id, 0) + 1

        schedule = task.schedule
        # 如果有执行次数限制,且已达到次数,则停止
        if schedule.frequency > 0 and self.job_counts[job_id] >= schedule.frequency:
            logger.info(f"作业 {job_id} 已达到其执行频率 {schedule.frequency} 次, 将不再调度。")
            return

        # 如果是 delay 模式,需要在这里手动安排下一次执行
        if schedule.mode == "delay" and schedule.seconds is not None:
            next_run_time = datetime.now() + timedelta(seconds=schedule.seconds)
            self.scheduler.add_job(
                self._execute_job,
                "date",
                run_date=next_run_time,
                args=[task, device],
                id=f"{job_id}_adhoc_{self.job_counts[job_id]}",
            )
            logger.info(f"作业 {job_id} (delay模式) 已安排下一次运行于 {next_run_time}")

    def schedule_all_tasks(self):
        """根据当前配置安排所有启用的任务。"""
        self.scheduler.remove_all_jobs()
        self.job_counts.clear()
        self.task_signatures.clear()
        logger.info("清空现有作业, 开始根据新配置重新调度...")

        for task in self.config.tasks:
            # 生成并保存任务签名
            self.task_signatures[task.alias] = self.get_task_signature(task)

            if not task.enabled:
                continue

            self._schedule_single_task(task, self.device_map)

    def get_task_signature(self, task: TaskConfig) -> str:
        """生成任务签名用于对比变更"""
        # 创建任务的关键属性字典
        task_data = {
            "alias": task.alias,
            "enabled": task.enabled,
            "protocol": task.protocol,
            "targets": sorted(task.targets),  # 排序确保一致性
            "storage": task.storage,
            "schedule": {
                "frequency": task.schedule.frequency,
                "mode": task.schedule.mode,
                "seconds": task.schedule.seconds,
            },
        }

        # 添加协议特定的属性
        if task.protocol == "ssh":
            task_data["command"] = task.command
        elif task.protocol == "snmp":
            task_data["type"] = task.type
            task_data["oid"] = task.oid

        # 添加解析配置
        if task.parse:
            task_data["parse"] = {
                "regex": task.parse.regex,
                "calculate": task.parse.calculate,
            }

        if task.labels:
            task_data["labels"] = task.labels

        # 生成MD5签名
        task_json = json.dumps(task_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(task_json.encode("utf-8")).hexdigest()

    def compare_configs(self, new_config: AppConfig) -> dict:
        """对比新旧配置, 返回变更信息"""
        changes = {
            "added": [],  # 新增的任务
            "removed": [],  # 删除的任务
            "modified": [],  # 修改的任务
            "unchanged": [],  # 未变更的任务
        }

        # 构建新配置的任务映射和签名
        new_tasks = {task.alias: task for task in new_config.tasks}
        new_signatures = {alias: self.get_task_signature(task) for alias, task in new_tasks.items()}

        # 构建旧配置的任务映射
        old_tasks = {task.alias: task for task in self.config.tasks}

        # 检查每个新任务
        for alias, _ in new_tasks.items():
            if alias not in old_tasks:
                changes["added"].append(alias)
            elif new_signatures[alias] != self.task_signatures.get(alias):
                changes["modified"].append(alias)
            else:
                changes["unchanged"].append(alias)

        # 检查删除的任务
        for alias in old_tasks:
            if alias not in new_tasks:
                changes["removed"].append(alias)

        return changes

    def update_tasks_incrementally(self, new_config: AppConfig):
        """增量更新任务调度"""
        logger.info("开始增量更新任务调度...")

        # 对比配置变更
        changes = self.compare_configs(new_config)

        # 更新设备映射
        new_device_map = {device.name: device for device in new_config.devices}

        # 记录变更统计
        total_changes = len(changes["added"]) + len(changes["removed"]) + len(changes["modified"])
        if total_changes == 0:
            logger.info("配置无变更, 跳过任务调度更新")
            return

        logger.info(
            f"检测到配置变更: 新增{len(changes['added'])}个, 删除{len(changes['removed'])}个, 修改{len(changes['modified'])}个, 未变更{len(changes['unchanged'])}个"
        )

        # 处理删除的任务
        for alias in changes["removed"]:
            self._remove_task_jobs(alias)
            if alias in self.task_signatures:
                del self.task_signatures[alias]
            logger.info(f"已删除任务: {alias}")

        # 处理修改的任务
        for alias in changes["modified"]:
            self._remove_task_jobs(alias)
            task = next(t for t in new_config.tasks if t.alias == alias)
            self._schedule_single_task(task, new_device_map)
            self.task_signatures[alias] = self.get_task_signature(task)
            logger.info(f"已更新任务: {alias}")

        # 处理新增的任务
        for alias in changes["added"]:
            task = next(t for t in new_config.tasks if t.alias == alias)
            self._schedule_single_task(task, new_device_map)
            self.task_signatures[alias] = self.get_task_signature(task)
            logger.info(f"已添加任务: {alias}")

        # 更新配置和设备映射
        self.config = new_config
        self.device_map = new_device_map

        logger.success(f"增量更新完成! 共处理 {total_changes} 个变更")

    def _remove_task_jobs(self, task_alias: str):
        """移除指定任务的所有作业"""
        jobs_to_remove = []
        for job in self.scheduler.get_jobs():
            if job.id.startswith(f"{task_alias}_"):
                jobs_to_remove.append(job.id)

        for job_id in jobs_to_remove:
            self.remove_job(job_id)
            # 清理作业计数
            if job_id in self.job_counts:
                del self.job_counts[job_id]

    def _schedule_single_task(self, task: TaskConfig, device_map: dict[str, DeviceConfig]):
        """为单个任务安排调度"""
        if not task.enabled:
            logger.info(f"任务 {task.alias} 已禁用, 跳过调度")
            return

        for device_name in task.targets:
            device = device_map.get(device_name)
            if not device:
                logger.warning(f"任务 {task.alias} 的目标设备 {device_name} 未在配置中定义, 已跳过")
                continue

            self.schedule_task_for_device(task, device)

    def reload_config_and_update_tasks(self, new_config: AppConfig):
        """重新加载配置并增量更新任务"""
        if new_config:
            self.update_tasks_incrementally(new_config)
        else:
            logger.error("新配置为空, 保持当前调度不变")

    def start(self):
        logger.info("启动调度器...")
        self.scheduler.start()

    def stop(self):
        logger.info("关闭调度器...")
        self.scheduler.shutdown()

    def remove_job(self, job_id: str):
        """从调度器中移除指定作业"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"已从调度器移除作业 {job_id}")
        except Exception as e:
            logger.warning(f"从调度器移除作业 {job_id} 失败: {e}")

    def schedule_task_for_device(self, task: TaskConfig, device: DeviceConfig):
        """为特定设备安排任务"""
        job_id = f"{task.alias}_{device.name}"
        schedule = task.schedule

        # 如果任务已存在,先移除
        self.remove_job(job_id)

        # 如果任务被禁用,则不安排
        if not task.enabled:
            logger.info(f"任务 {task.alias} 已禁用,不会安排作业")
            return

        # 安排新作业
        if schedule.frequency == 1:
            self.scheduler.add_job(
                self._execute_job,
                "date",
                run_date=datetime.now() + timedelta(seconds=1),
                args=[task, device],
                id=job_id,
            )
            logger.info(f"已安排作业 {job_id} (仅执行一次)。")
        elif schedule.mode == "interval" and schedule.seconds is not None:
            self.scheduler.add_job(
                self._execute_job, IntervalTrigger(seconds=schedule.seconds), args=[task, device], id=job_id
            )
            logger.info(f"已安排作业 {job_id} (interval模式, 每 {schedule.seconds} 秒)。")
        elif schedule.mode == "delay":
            # delay 模式的第一次执行是立即执行
            self.scheduler.add_job(
                self._execute_job,
                "date",
                run_date=datetime.now() + timedelta(seconds=1),
                args=[task, device],
                id=job_id,
            )
            logger.info(f"已安排作业 {job_id} (delay模式, 首次执行)。")
