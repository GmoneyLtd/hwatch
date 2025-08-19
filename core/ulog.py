import sys

from loguru import logger


def setup_logging(level: str = "INFO", rotation: str = "10 MB", retention: str = "7 days"):
    """
    配置全局日志记录器。

    Args:
        level (str): 控制台输出的最低日志级别。
        rotation (str): 日志文件轮转的大小阈值。
        retention (str): 日志文件的保留时间。
    """
    logger.remove()

    # 配置控制台输出
    _ = logger.add(
        sys.stderr,
        level=level.upper(),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        ),
        colorize=True,
    )

    # 通用应用日志, 只记录主应用(__main__)和应用状态相关的日志
    _ = logger.add(
        "log/app.log",
        level="DEBUG",
        filter=lambda record: record["name"] is not None and (record["name"] in ["__main__", "core.ulog", "core.config_loader", "core.database"] or (record["name"].startswith("core.") and not any(mod in record["name"] for mod in ["collector", "scheduler", "web_server", "watch"]))),
        rotation=rotation,
        retention=retention,
        enqueue=True,  # 使日志记录在多线程/多进程环境中安全
        backtrace=True,
        diagnose=True,
        format="{time} {level} {name}:{function}:{line} {message}",
    )

    # 按模块分离日志文件
    log_modules = ["collector", "scheduler", "web_server", "database", "watch", "config_loader"]
    for module_name in log_modules:
        _ = logger.add(
            f"log/{module_name}.log",
            level="DEBUG",
            filter=lambda record, module=module_name: record["name"] == f"core.{module}" or record["name"].startswith(f"core.{module}."),
            rotation=rotation,
            retention=retention,
            enqueue=True,
            format="{time} {level} {name}:{function}:{line} {message}",
        )

    logger.info(f"日志系统初始化完成, 控制台级别: {level.upper()}")
