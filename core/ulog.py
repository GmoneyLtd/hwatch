
import sys
from loguru import logger

def setup_logging(level="INFO", rotation="10 MB", retention="7 days"):
    """
    配置全局日志记录器。

    Args:
        level (str): 控制台输出的最低日志级别。
        rotation (str): 日志文件轮转的大小阈值。
        retention (str): 日志文件的保留时间。
    """
    logger.remove()

    # 配置控制台输出
    logger.add(
        sys.stderr,
        level=level.upper(),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        ),
        colorize=True,
    )

    # 通用应用日志，记录所有模块的DEBUG及以上级别日志
    logger.add(
        "log/app.log",
        level="DEBUG",
        rotation=rotation,
        retention=retention,
        enqueue=True,  # 使日志记录在多线程/多进程环境中安全
        backtrace=True,
        diagnose=True,
        format="{time} {level} {name}:{function}:{line} {message}",
    )

    # 按模块分离日志文件
    log_modules = ["collector", "scheduler", "web_server", "database", "watch"]
    for module_name in log_modules:
        logger.add(
            f"log/{module_name}.log",
            level="DEBUG",
            filter=lambda record: record["name"].startswith(f"core.{module_name}"),
            rotation=rotation,
            retention=retention,
            enqueue=True,
            format="{time} {level} {message}",
        )

    logger.info(f"日志系统初始化完成，控制台级别: {level.upper()}")

