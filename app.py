import argparse
import asyncio
import os
import signal
import sys

import uvicorn
from loguru import logger

from core.batch_writer import batch_writer
from core.collector import cleanup_all_connections
from core.config_loader import AppConfig, load_config
from core.database import close_db, init_db
from core.file_buffer import get_file_buffer

# Import optimization modules
from core.performance_monitor import performance_monitor
from core.scheduler import TaskScheduler

# Import core modules
from core.ulog import setup_logging
from core.watch import start_watching, stop_watching
from core.web_server import app, app_state

# --- Global variables ---
CONFIG_PATH = "config.yaml"

# Global components for graceful shutdown
_scheduler: TaskScheduler | None = None
_server: uvicorn.Server | None = None
_shutdown_event = asyncio.Event()


async def graceful_shutdown():
    """Perform graceful shutdown of all components"""
    logger.info("Starting graceful shutdown...")

    try:
        # 1. Stop accepting new web requests
        if _server:
            logger.info("Stopping web server...")
            _server.should_exit = True

        # 2. Stop file monitoring
        logger.info("Stopping file monitoring...")
        stop_watching()

        # 3. Stop task scheduler (wait for running tasks)
        if _scheduler:
            logger.info("Stopping task scheduler...")
            _scheduler.stop(wait_timeout=5)

        # 4. Cleanup all connections
        logger.info("Cleaning up connections...")
        await cleanup_all_connections()

        # 5. Shutdown optimization components
        logger.info("Shutting down optimization components...")
        from core.batch_writer import shutdown_batch_writer
        from core.file_buffer import shutdown_file_buffer

        await shutdown_batch_writer()
        await shutdown_file_buffer()

        # 6. Close database connection
        logger.info("Closing database connection...")
        await close_db()

        logger.info("Graceful shutdown completed successfully")

    except Exception as e:
        logger.error(f"Error during graceful shutdown: {e}")
    finally:
        # Set shutdown event to signal main loop to exit
        _shutdown_event.set()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    # Create task for graceful shutdown
    try:
        loop = asyncio.get_running_loop()
        shutdown_task = loop.create_task(graceful_shutdown())
        # Store reference to prevent garbage collection
        shutdown_task.add_done_callback(lambda t: None)
    except RuntimeError:
        # If no running loop, just exit
        logger.warning("No running event loop, exiting immediately")
        sys.exit(0)


# --- Main application logic ---
def reload_config_and_reschedule(scheduler: TaskScheduler):
    """Callback function: Reload configuration and incrementally update scheduler."""
    logger.info("Configuration change detected, starting reload...")
    new_config = load_config(CONFIG_PATH)
    if new_config:
        # Update configuration held by web server
        app_state["config"] = new_config

        # Use incremental update mechanism
        scheduler.reload_config_and_update_tasks(new_config)
        logger.success("Configuration reload and task incremental update successful!")
    else:
        logger.error("Failed to load new configuration, scheduler will continue running with old configuration.")


async def main():
    """Main application entry point."""
    global _scheduler, _server

    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 1. Parse command line arguments
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    parser = argparse.ArgumentParser(description="Hwatch - Lightweight Operations Collection Platform")
    parser.add_argument(
        "--level",
        default="WARNING",  # Default value for command line argument
        choices=valid_levels,
        help="Set console log level",
    )
    args = parser.parse_args()

    # 2. Check environment variables, environment variables have highest priority
    env_log_level = os.getenv("LOG_LEVEL")
    if env_log_level:
        env_log_level = env_log_level.upper()
        if env_log_level in valid_levels:
            final_log_level = env_log_level
            log_source = "environment variable"
        else:
            logger.warning(
                f"Invalid LOG_LEVEL environment variable value: {env_log_level}, using command line argument: {args.level}"
            )
            final_log_level = args.level
            log_source = "command line argument (invalid environment variable)"
    else:
        final_log_level = args.level
        log_source = "command line argument"

    # 3. Initialize logging system
    setup_logging(level=final_log_level)
    logger.info(f"Log level set to: {final_log_level} (source: {log_source})")

    # 4. Initialize database
    await init_db()

    # 5. Load initial configuration
    config = load_config(CONFIG_PATH)
    if not config:
        logger.error(f"Unable to load initial configuration {CONFIG_PATH}, exiting program.")
        return

    # 6. Initialize scheduler
    _scheduler = TaskScheduler(config)

    # 7. Set up web application state machine
    app_state["config"] = config
    app_state["config_path"] = CONFIG_PATH
    app_state["scheduler"] = _scheduler
    app_state["reload_callback"] = lambda: reload_config_and_reschedule(_scheduler)

    # 8. Schedule all tasks for the first time
    _scheduler.schedule_all_tasks()

    # 9. Start file monitoring
    start_watching(CONFIG_PATH, app_state["reload_callback"])

    # 10. Start scheduler
    _scheduler.start()

    # 11. Configure and start Uvicorn web server
    uvicorn_config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level=args.level.lower())
    _server = uvicorn.Server(uvicorn_config)

    logger.info("Hwatch application started successfully! Access http://localhost:8080")

    try:
        # Run server and wait for shutdown signal
        server_task = asyncio.create_task(_server.serve())
        shutdown_task = asyncio.create_task(_shutdown_event.wait())

        # Wait for either server to finish or shutdown signal
        _, pending = await asyncio.wait([server_task, shutdown_task], return_when=asyncio.FIRST_COMPLETED)

        # Cancel any pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        logger.error(f"Error in main loop: {e}")

    logger.info("Hwatch application has been shutdown.")


if __name__ == "__main__":
    asyncio.run(main())
