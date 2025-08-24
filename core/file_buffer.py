import asyncio
import os
import time
from collections import defaultdict

import aiofiles
from loguru import logger


class AsyncFileBuffer:
    """异步文件缓冲器, 提升文件I/O性能"""

    def __init__(self, buffer_size: int = 8192, flush_interval: float = 5.0):
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval

        # 每个文件的缓冲区
        self.buffers: defaultdict[str, list[str]] = defaultdict(list)
        self.buffer_sizes: defaultdict[str, int] = defaultdict(int)
        self.last_flush: defaultdict[str, float] = defaultdict(float)

        # 每个文件的锁
        self.file_locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

        # 定时刷新任务
        self._flush_task: asyncio.Task | None = None
        self._shutdown = False
        self._start_periodic_flush()

    def _start_periodic_flush(self):
        """启动定时刷新任务"""
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._periodic_flush())

    async def _periodic_flush(self):
        """定期刷新所有文件缓冲区"""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_all_files()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic file flush error: {e}")

    async def write_buffered(self, filepath: str, content: str):
        """缓冲写入文件"""
        if self._shutdown:
            return False

        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        async with self.file_locks[filepath]:
            # 添加到缓冲区
            self.buffers[filepath].append(content)
            self.buffer_sizes[filepath] += len(content)

            current_time = time.time()

            # 检查是否需要刷新
            should_flush = (
                self.buffer_sizes[filepath] >= self.buffer_size
                or current_time - self.last_flush[filepath] >= self.flush_interval
            )

            if should_flush:
                await self._flush_file(filepath)

        return True

    async def _flush_file(self, filepath: str):
        """刷新单个文件的缓冲区"""
        if not self.buffers[filepath]:
            return

        content_to_write = "".join(self.buffers[filepath])
        entry_count = len(self.buffers[filepath])

        try:
            async with aiofiles.open(filepath, "a", encoding="utf-8") as f:
                await f.write(content_to_write)

            logger.debug(f"Flushed {entry_count} entries to {filepath}")

            # 清空缓冲区
            self.buffers[filepath].clear()
            self.buffer_sizes[filepath] = 0
            self.last_flush[filepath] = time.time()

            return True

        except Exception as e:
            logger.error(f"File flush failed for {filepath}: {e}")
            return False

    async def _flush_all_files(self):
        """刷新所有文件的缓冲区"""
        current_time = time.time()

        for filepath in list(self.buffers.keys()):
            if self.buffers[filepath] and current_time - self.last_flush[filepath] >= self.flush_interval:
                async with self.file_locks[filepath]:
                    await self._flush_file(filepath)

    async def flush_all(self):
        """手动刷新所有文件"""
        for filepath in list(self.buffers.keys()):
            async with self.file_locks[filepath]:
                await self._flush_file(filepath)

    async def shutdown(self):
        """关闭文件缓冲器"""
        self._shutdown = True

        # 取消定时任务
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # 最后一次刷新所有文件
        await self.flush_all()
        logger.info("Async file buffer shutdown completed")


# 全局文件缓冲器实例
_file_buffer: AsyncFileBuffer | None = None


def get_file_buffer() -> AsyncFileBuffer:
    """获取全局文件缓冲器实例"""
    global _file_buffer
    if _file_buffer is None:
        _file_buffer = AsyncFileBuffer()
    return _file_buffer


async def shutdown_file_buffer():
    """关闭文件缓冲器"""
    global _file_buffer
    if _file_buffer:
        await _file_buffer.shutdown()
        _file_buffer = None
