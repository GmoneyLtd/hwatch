
import asyncio
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
        if task.storage == 'sqlite':
            await save_result(task.alias, device.name, {k: v for k, v in results.items() if k != 'raw_output'})
        elif task.storage == 'file':
            outfile_dir = "outfile"
            os.makedirs(outfile_dir, exist_ok=True)
            # 使用任务别名和设备名的组合作为文件名, 追加模式
            file_path = os.path.join(outfile_dir, f"{task.alias}_{device.name}.log")
            
            # 准备写入内容, 包含时间戳和任务信息
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            content_lines = [
                f"============ {timestamp} ============",
                f"Task: {task.alias}",
                f"Device: {device.name} ({device.ip})",
                f"Protocol: {task.protocol}",
            ]
            
            # 添加具体的任务参数
            if task.protocol == 'ssh' and task.command:
                content_lines.append(f"Commadn: {task.command[0]}")
            elif task.protocol == 'snmp' and task.oid:
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
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write('\n'.join(content_lines) + '\n')
            logger.info(f"作业 {job_id} 的结果已追加到 {file_path}")
        
        # 处理执行频率和 'delay' 模式的重调度
        self.job_counts[job_id] = self.job_counts.get(job_id, 0) + 1
        
        schedule = task.schedule
        # 如果有执行次数限制,且已达到次数,则停止
        if schedule.frequency > 0 and self.job_counts[job_id] >= schedule.frequency:
            logger.info(f"作业 {job_id} 已达到其执行频率 {schedule.frequency} 次, 将不再调度。")
            return

        # 如果是 delay 模式,需要在这里手动安排下一次执行
        if schedule.mode == 'delay' and schedule.seconds is not None:
            next_run_time = datetime.now() + timedelta(seconds=schedule.seconds)
            self.scheduler.add_job(self._execute_job, 'date', run_date=next_run_time, args=[task, device], id=f"{job_id}_adhoc_{self.job_counts[job_id]}")
            logger.info(f"作业 {job_id} (delay模式) 已安排下一次运行于 {next_run_time}")

    def schedule_all_tasks(self):
        """根据当前配置安排所有启用的任务。"""
        self.scheduler.remove_all_jobs()
        self.job_counts.clear()
        logger.info("清空现有作业, 开始根据新配置重新调度...")

        for task in self.config.tasks:
            if not task.enabled:
                continue

            for device_name in task.targets:
                device = self.device_map.get(device_name)
                if not device:
                    logger.warning(f"任务 {task.alias} 的目标设备 {device_name} 未在配置中定义,已跳过。")
                    continue
                
                job_id = f"{task.alias}_{device.name}"
                schedule = task.schedule

                # 如果是仅执行一次的任务
                if schedule.frequency == 1:
                    self.scheduler.add_job(self._execute_job, 'date', run_date=datetime.now() + timedelta(seconds=1), args=[task, device], id=job_id)
                    logger.info(f"已安排作业 {job_id} (仅执行一次)。")
                    continue

                # 对于循环任务
                if schedule.mode == 'interval' and schedule.seconds is not None:
                    self.scheduler.add_job(self._execute_job, IntervalTrigger(seconds=schedule.seconds), args=[task, device], id=job_id)
                    logger.info(f"已安排作业 {job_id} (interval模式, 每 {schedule.seconds} 秒)。")
                elif schedule.mode == 'delay':
                    # delay 模式的第一次执行是立即执行
                    self.scheduler.add_job(self._execute_job, 'date', run_date=datetime.now() + timedelta(seconds=1), args=[task, device], id=job_id)
                    logger.info(f"已安排作业 {job_id} (delay模式, 首次执行)。")

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
            self.scheduler.add_job(self._execute_job, 'date', run_date=datetime.now() + timedelta(seconds=1), args=[task, device], id=job_id)
            logger.info(f"已安排作业 {job_id} (仅执行一次)。")
        elif schedule.mode == 'interval' and schedule.seconds is not None:
            self.scheduler.add_job(self._execute_job, IntervalTrigger(seconds=schedule.seconds), args=[task, device], id=job_id)
            logger.info(f"已安排作业 {job_id} (interval模式, 每 {schedule.seconds} 秒)。")
        elif schedule.mode == 'delay':
            # delay 模式的第一次执行是立即执行
            self.scheduler.add_job(self._execute_job, 'date', run_date=datetime.now() + timedelta(seconds=1), args=[task, device], id=job_id)
            logger.info(f"已安排作业 {job_id} (delay模式, 首次执行)。")
