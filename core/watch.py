from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import override

from loguru import logger
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


class AsyncConfigChangeHandler(FileSystemEventHandler):
    """Async file system event handler for monitoring configuration file changes."""

    config_file: str
    callback: Callable[[], Awaitable[None]]
    loop: asyncio.AbstractEventLoop

    def __init__(self, config_file: str, callback: Callable[[], Awaitable[None]]) -> None:
        """Initialize async configuration file change handler.

        Args:
            config_file: Path to the configuration file to monitor
            callback: Async callback function to call when file is modified
        """
        super().__init__()
        self.config_file = os.path.abspath(config_file)
        self.callback = callback
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError as e:
            logger.error(f"Unable to get running event loop: {e}")
            raise

    @override
    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events.

        Args:
            event: File system modification event
        """
        if self._should_trigger_callback(event):
            self._schedule_callback()

    def _should_trigger_callback(self, event: FileSystemEvent) -> bool:
        """Check if callback should be triggered.

        Args:
            event: File system modification event

        Returns:
            Returns True if callback should be triggered, otherwise returns False
        """
        return not event.is_directory and os.path.abspath(event.src_path) == self.config_file

    def _schedule_callback(self) -> None:
        """Safely schedule async callback in event loop."""
        logger.info(f"Configuration file {self.config_file} has been modified. Triggering callback...")
        try:
            # Ensure callback() returns a coroutine
            coro = self.callback()
            if asyncio.iscoroutine(coro):
                _ = asyncio.run_coroutine_threadsafe(coro, self.loop)
        except Exception as e:
            logger.error(f"Error occurred while scheduling callback function: {e}")


def start_watching(config_file: str, callback: Callable[[], Awaitable[None]]):
    """Start a background thread to monitor configuration file.

    Args:
        config_file: Path to the configuration file to monitor
        callback: Async callback function to call when file is modified

    Returns:
        Observer instance, or None if startup fails
    """
    try:
        return _create_and_start_observer(config_file, callback)
    except Exception as e:
        logger.error(f"Error occurred while starting file monitoring: {e}")
        return None


def _create_and_start_observer(config_file: str, callback: Callable[[], Awaitable[None]]):
    """Create and start file observer.

    Args:
        config_file: Path to the configuration file to monitor
        callback: Async callback function to call when file is modified

    Returns:
        Observer instance, or None if startup fails
    """
    path = os.path.dirname(os.path.abspath(config_file))

    if not _validate_watch_path(path):
        return None

    event_handler = AsyncConfigChangeHandler(config_file, callback)
    observer = Observer()
    _ = observer.schedule(event_handler, path, recursive=False)
    observer.start()

    logger.info(f"Started background monitoring for {config_file}.")
    return observer


def _validate_watch_path(path: str) -> bool:
    """Validate if monitoring path is valid.

    Args:
        path: Path to validate

    Returns:
        Returns True if path is valid, otherwise returns False
    """
    if not os.path.exists(path):
        logger.warning(f"Monitoring directory {path} does not exist, unable to start monitoring.")
        return False
    return True
