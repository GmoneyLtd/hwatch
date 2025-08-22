import os
import sys
from collections.abc import Callable

from loguru import logger

# Log format definitions
CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

FILE_FORMAT = "{time} {level: <8} {name}:{function}:{line} {message}"

# Core module list
CORE_MODULES = ["collector", "scheduler", "web_server", "database", "watch", "config_loader", "ulog"]


def create_module_filter(target_modules: list[str], include: bool = True) -> Callable[..., bool]:
    """Create module filter function.

    Args:
        target_modules: Target module list
        include: True means include these modules, False means exclude these modules

    Returns:
        Filter function
    """

    def filter_func(record: dict[str, object]) -> bool:
        if record["name"] is None:
            return False

        # Handle main module
        if record["name"] == "__main__":
            return include

        # Check if it's a target module
        for module in target_modules:
            module_path = f"core.{module}"
            name = record["name"]
            if isinstance(name, str):
                if name == module_path or name.startswith(f"{module_path}."):
                    return include

        # For other core modules
        name = record["name"]
        if isinstance(name, str) and name.startswith("core."):
            return not include

        return False

    return filter_func


def setup_logging(
    level: str = "INFO",
    rotation: str = "10 MB",
    retention: str = "7 days",
    log_dir: str = "log",
    modules: list[str] | None = None,
):
    """Configure global logger.

    Args:
        level: Minimum log level for console output
        rotation: Log file rotation size threshold
        retention: Log file retention time
        log_dir: Log file storage directory
        modules: List of modules to log separately, defaults to None means using CORE_MODULES
    """
    # Ensure log directory exists
    try:
        # Check if directory exists first
        if not os.path.exists(log_dir):
            logger.debug(f"Log directory {log_dir} does not exist, creating...")
            os.makedirs(log_dir)
            logger.debug(f"Successfully created log directory: {log_dir}")

        # Verify directory is writable
        if not os.access(log_dir, os.W_OK):
            logger.warning(f"Log directory {log_dir} is not writable, will use temporary directory")
            import tempfile

            log_dir = tempfile.gettempdir()
            logger.info(f"Using temporary directory as log directory: {log_dir}")
    except Exception as e:
        logger.error(f"Failed to handle log directory {log_dir}: {e}")
        import tempfile

        log_dir = tempfile.gettempdir()
        logger.info(f"Using temporary directory as log directory: {log_dir}")

    # Remove all existing handlers
    logger.remove()

    # Configure console output
    _ = logger.add(
        sys.stderr,
        level=level.upper(),
        format=CONSOLE_FORMAT,
        colorize=True,
    )

    # General application log configuration
    app_modules = ["ulog", "config_loader", "database"]
    app_filter = create_module_filter(app_modules, include=True)

    _ = logger.add(
        f"{log_dir}/app.log",
        level="DEBUG",
        filter=app_filter,
        rotation=rotation,
        retention=retention,
        enqueue=True,
        backtrace=True,
        diagnose=True,
        format=FILE_FORMAT,
    )

    # Separate log files by module
    modules_to_log = modules or CORE_MODULES

    for module_name in modules_to_log:
        module_filter = create_module_filter([module_name], include=True)

        _ = logger.add(
            f"{log_dir}/{module_name}.log",
            level="DEBUG",
            filter=module_filter,
            rotation=rotation,
            retention=retention,
            enqueue=True,
            format=FILE_FORMAT,
        )

    logger.info(f"Log system initialized, console level: {level.upper()}, log directory: {log_dir}")


def get_logger(name: str | None = None):
    """Get named logger.

    Args:
        name: Logger name, defaults to None uses caller's module name

    Returns:
        Configured logger instance
    """
    return logger.bind(name=name)
