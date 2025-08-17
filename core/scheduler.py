
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from loguru import logger
import os

from core.config_loader import AppConfig, TaskConfig, DeviceConfig
from core.collector import run_task
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
            logger.warning(f"作业 {job_id} 未返回结果 (可能被禁用或执行失败)。")
            return

        # 根据存储策略处理结果
        if task.storage == 'sqlite':
            await save_result(task.alias, device.name, {k: v for k, v in results.items() if k != 'raw_output'})
        elif task.storage == 'file':
            outfile_dir = "outfile"
            os.makedirs(outfile_dir, exist_ok=True)
            file_path = os.path.join(outfile_dir, f"{job_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.log")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(results.get("raw_output", ""))
            logger.info(f"作业 {job_id} 的结果已保存到 {file_path}")
        
        # 处理执行频率和 'delay' 模式的重调度
        self.job_counts[job_id] = self.job_counts.get(job_id, 0) + 1
        
        schedule = task.schedule
        # 如果有执行次数限制，且已达到次数，则停止
        if schedule.frequency > 0 and self.job_counts[job_id] >= schedule.frequency:
            logger.info(f"作业 {job_id} 已达到其执行频率 {schedule.frequency} 次，将不再调度。")
            return

        # 如果是 delay 模式，需要在这里手动安排下一次执行
        if schedule.mode == 'delay':
            next_run_time = datetime.now() + timedelta(seconds=schedule.seconds)
            self.scheduler.add_job(self._execute_job, 'date', run_date=next_run_time, args=[task, device], id=f"{job_id}_adhoc_{self.job_counts[job_id]}")
            logger.info(f"作业 {job_id} (delay模式) 已安排下一次运行于 {next_run_time}")

    def schedule_all_tasks(self):
        """根据当前配置安排所有启用的任务。"""
        self.scheduler.remove_all_jobs()
        self.job_counts.clear()
        logger.info("清空现有作业，开始根据新配置重新调度...")

        for task in self.config.tasks:
            if not task.enabled:
                continue

            for device_name in task.targets:
                device = self.device_map.get(device_name)
                if not device:
                    logger.warning(f"任务 {task.alias} 的目标设备 {device_name} 未在配置中定义，已跳过。")
                    continue
                
                job_id = f"{task.alias}_{device.name}"
                schedule = task.schedule

                # 如果是仅执行一次的任务
                if schedule.frequency == 1:
                    self.scheduler.add_job(self._execute_job, 'date', run_date=datetime.now() + timedelta(seconds=1), args=[task, device], id=job_id)
                    logger.info(f"已安排作业 {job_id} (仅执行一次)。")
                    continue

                # 对于循环任务
                if schedule.mode == 'interval':
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

