import asyncio
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

from loguru import logger

from core.database import _get_connection


class BatchDatabaseWriter:
    """批量数据库写入器, 提升数据库写入性能"""

    def __init__(self, batch_size: int = 100, flush_interval: float = 5.0, max_memory_mb: int = 10):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_memory = max_memory_mb * 1024 * 1024
        self.buffer: list[tuple] = []
        self.buffer_size = 0
        self.last_flush = time.time()
        self.flush_lock = asyncio.Lock()
        self._flush_task: asyncio.Task | None = None
        self._shutdown = False

        # 启动定时刷新任务
        self._start_periodic_flush()

    def _start_periodic_flush(self):
        """启动定时刷新任务"""
        try:
            # 检查是否有运行中的事件循环
            _ = asyncio.get_running_loop()
            if self._flush_task is None or self._flush_task.done():
                self._flush_task = asyncio.create_task(self._periodic_flush())
        except RuntimeError:
            # 没有运行中的事件循环, 延迟启动任务
            self._flush_task = None

    async def _periodic_flush(self):
        """定期刷新缓冲区"""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.flush_interval)
                if time.time() - self.last_flush >= self.flush_interval:
                    await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic flush error: {e}")

    def _ensure_flush_task_started(self):
        """确保定时刷新任务已启动"""
        if self._flush_task is None:
            try:
                self._flush_task = asyncio.create_task(self._periodic_flush())
            except RuntimeError:
                # 仍然没有事件循环, 忽略
                pass

    async def add_record(self, task_alias: str, device_name: str, results: dict[str, Any]):
        """添加记录到批量写入缓冲区"""
        if self._shutdown:
            return False

        # 确保定时刷新任务已启动
        self._ensure_flush_task_started()

        timestamp = datetime.now()

        # 将结果字典转换为多个记录
        records = []
        for key, value in results.items():
            if key != "raw_output":  # 跳过raw_output
                record = (timestamp, task_alias, device_name, key, str(value))
                records.append(record)

        if not records:
            return True

        async with self.flush_lock:
            # 添加到缓冲区
            self.buffer.extend(records)

            # 估算内存使用
            record_size = sum(len(str(r)) for r in records)
            self.buffer_size += record_size

            # 检查是否需要立即刷新
            should_flush = (
                len(self.buffer) >= self.batch_size
                or self.buffer_size >= self.max_memory
                or time.time() - self.last_flush >= self.flush_interval
            )

            if should_flush:
                await self._flush_buffer()

        return True

    async def flush(self):
        """手动刷新缓冲区"""
        async with self.flush_lock:
            await self._flush_buffer()

    async def _flush_buffer(self):
        """内部刷新缓冲区实现"""
        if not self.buffer:
            return

        records_to_write = self.buffer.copy()
        record_count = len(records_to_write)

        try:
            conn = await _get_connection()

            # 批量插入
            await conn.executemany(
                "INSERT INTO task_results (timestamp, task_alias, device_name, key, value) VALUES (?, ?, ?, ?, ?)",
                records_to_write,
            )
            await conn.commit()

            logger.debug(f"Batch wrote {record_count} records to database")

            # 清空缓冲区
            self.buffer.clear()
            self.buffer_size = 0
            self.last_flush = time.time()

            return True

        except Exception as e:
            logger.error(f"Batch database write failed: {e}")
            # 发生错误时不清空缓冲区, 等待下次重试
            return False

    async def shutdown(self):
        """关闭批量写入器"""
        self._shutdown = True

        # 取消定时任务
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # 最后一次刷新
        await self.flush()
        logger.info("Batch database writer shutdown completed")


# 全局批量写入器实例
_batch_writer: BatchDatabaseWriter | None = None


def get_batch_writer() -> BatchDatabaseWriter:
    """获取全局批量写入器实例"""
    global _batch_writer
    if _batch_writer is None:
        _batch_writer = BatchDatabaseWriter()
    return _batch_writer


async def batch_save_result(task_alias: str, device_name: str, results: dict[str, Any]) -> bool:
    """批量保存任务结果"""
    writer = get_batch_writer()
    return await writer.add_record(task_alias, device_name, results)


async def shutdown_batch_writer():
    """关闭批量写入器"""
    global _batch_writer
    if _batch_writer:
        await _batch_writer.shutdown()
        _batch_writer = None


# Create global instance for easy import
batch_writer = get_batch_writer()

# Export public interface
__all__ = ["BatchDatabaseWriter", "batch_save_result", "batch_writer", "shutdown_batch_writer"]
