
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from loguru import logger
from typing import Callable, Awaitable
import os

class AsyncConfigChangeHandler(FileSystemEventHandler):
    """异步文件系统事件处理器，用于监控配置文件更改。"""
    def __init__(self, config_file: str, callback: Callable[[], Awaitable[None]]):
        self.config_file = os.path.abspath(config_file)
        self.callback = callback
        self.loop = asyncio.get_running_loop()

    def on_modified(self, event: FileModifiedEvent):
        if not event.is_directory and os.path.abspath(event.src_path) == self.config_file:
            logger.info(f"检测到配置文件 {self.config_file} 已被修改。触发回调...")
            # 在主事件循环中安全地调度异步回调
            asyncio.run_coroutine_threadsafe(self.callback(), self.loop)

def start_watching(config_file: str, callback: Callable[[], Awaitable[None]]):
    """
    启动一个后台线程来监控配置文件。

    Args:
        config_file (str): 要监控的配置文件的路径。
        callback (Callable[[], Awaitable[None]]): 文件修改时要调用的异步回调函数。
    """
    path = os.path.dirname(os.path.abspath(config_file))
    if not os.path.exists(path):
        logger.warning(f"监控目录 {path} 不存在，无法启动监控。")
        return

    event_handler = AsyncConfigChangeHandler(config_file, callback)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()
    logger.info(f"已启动对 {config_file} 的后台监控。")
    return observer

