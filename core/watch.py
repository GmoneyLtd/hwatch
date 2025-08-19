
from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import override

from loguru import logger
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer


class AsyncConfigChangeHandler(FileSystemEventHandler):
    """异步文件系统事件处理器，用于监控配置文件更改."""
    
    config_file: str
    callback: Callable[[], Awaitable[None]]
    loop: asyncio.AbstractEventLoop

    def __init__(self, config_file: str, callback: Callable[[], Awaitable[None]]) -> None:
        """初始化异步配置文件变更处理器.

        Args:
            config_file: 要监控的配置文件路径
            callback: 文件修改时要调用的异步回调函数
        """
        super().__init__()
        self.config_file = os.path.abspath(config_file)
        self.callback = callback
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError as e:
            logger.error(f"无法获取运行中的事件循环: {e}")
            raise

    @override
    def on_modified(self, event: FileSystemEvent) -> None:
        """处理文件修改事件.

        Args:
            event: 文件系统修改事件
        """
        if self._should_trigger_callback(event):
            self._schedule_callback()

    def _should_trigger_callback(self, event: FileSystemEvent) -> bool:
        """检查是否应该触发回调函数.

        Args:
            event: 文件系统修改事件

        Returns:
            如果应该触发回调则返回True, 否则返回False
        """
        return (
            not event.is_directory 
            and os.path.abspath(event.src_path) == self.config_file
        )

    def _schedule_callback(self) -> None:
        """在事件循环中安全地调度异步回调."""
        logger.info(f"检测到配置文件 {self.config_file} 已被修改。触发回调...")
        try:
            # 确保 callback() 返回的是协程
            coro = self.callback()
            if asyncio.iscoroutine(coro):
                _ = asyncio.run_coroutine_threadsafe(coro, self.loop)
        except Exception as e:
            logger.error(f"调度回调函数时发生错误: {e}")


def start_watching(
    config_file: str, 
    callback: Callable[[], Awaitable[None]]
):
    """启动一个后台线程来监控配置文件.

    Args:
        config_file: 要监控的配置文件的路径
        callback: 文件修改时要调用的异步回调函数

    Returns:
        Observer实例, 如果启动失败则返回None
    """
    try:
        return _create_and_start_observer(config_file, callback)
    except Exception as e:
        logger.error(f"启动文件监控时发生错误: {e}")
        return None


def _create_and_start_observer(
    config_file: str, 
    callback: Callable[[], Awaitable[None]]
):
    """创建并启动文件观察器.

    Args:
        config_file: 要监控的配置文件的路径
        callback: 文件修改时要调用的异步回调函数

    Returns:
        Observer实例, 如果启动失败则返回None
    """
    path = os.path.dirname(os.path.abspath(config_file))
    
    if not _validate_watch_path(path):
        return None

    event_handler = AsyncConfigChangeHandler(config_file, callback)
    observer = Observer()
    _ = observer.schedule(event_handler, path, recursive=False)
    observer.start()
    
    logger.info(f"已启动对 {config_file} 的后台监控。")
    return observer


def _validate_watch_path(path: str) -> bool:
    """验证监控路径是否有效.

    Args:
        path: 要验证的路径

    Returns:
        如果路径有效则返回True, 否则返回False
    """
    if not os.path.exists(path):
        logger.warning(f"监控目录 {path} 不存在，无法启动监控。")
        return False
    return True

