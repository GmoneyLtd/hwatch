import os
import sys
from collections.abc import Callable

from loguru import logger

# 日志格式定义
CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

FILE_FORMAT = "{time} {level: <8} {name}:{function}:{line} {message}"

# 核心模块列表
CORE_MODULES = ["collector", "scheduler", "web_server", "database", "watch", "config_loader", "ulog"]


def create_module_filter(target_modules: list[str], include: bool = True) -> Callable[..., bool]:
    """创建模块过滤器函数。

    Args:
        target_modules: 目标模块列表
        include: True表示包含这些模块, False表示排除这些模块

    Returns:
        过滤器函数
    """

    def filter_func(record: dict[str, object]) -> bool:
        if record["name"] is None:
            return False

        # 处理主模块
        if record["name"] == "__main__":
            return include

        # 检查是否为目标模块
        for module in target_modules:
            module_path = f"core.{module}"
            name = record["name"]
            if isinstance(name, str):
                if name == module_path or name.startswith(f"{module_path}."):
                    return include

        # 对于其他core模块
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
    """配置全局日志记录器。

    Args:
        level: 控制台输出的最低日志级别
        rotation: 日志文件轮转的大小阈值
        retention: 日志文件的保留时间
        log_dir: 日志文件存储目录
        modules: 要单独记录的模块列表, 默认为None表示使用CORE_MODULES
    """
    # 确保日志目录存在
    try:
        # 先检查目录是否存在
        if not os.path.exists(log_dir):
            logger.debug(f"日志目录 {log_dir} 不存在, 正在创建...")
            os.makedirs(log_dir)
            logger.debug(f"成功创建日志目录: {log_dir}")

        # 验证目录是否可写
        if not os.access(log_dir, os.W_OK):
            logger.warning(f"日志目录 {log_dir} 不可写, 将使用临时目录")
            import tempfile

            log_dir = tempfile.gettempdir()
            logger.info(f"使用临时目录作为日志目录: {log_dir}")
    except Exception as e:
        logger.error(f"处理日志目录 {log_dir} 失败: {e}")
        import tempfile

        log_dir = tempfile.gettempdir()
        logger.info(f"使用临时目录作为日志目录: {log_dir}")

    # 移除所有现有处理器
    logger.remove()

    # 配置控制台输出
    _ = logger.add(
        sys.stderr,
        level=level.upper(),
        format=CONSOLE_FORMAT,
        colorize=True,
    )

    # 通用应用日志配置
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

    # 按模块分离日志文件
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

    logger.info(f"日志系统初始化完成, 控制台级别: {level.upper()}, 日志目录: {log_dir}")


def get_logger(name: str | None = None):
    """获取命名的日志记录器。

    Args:
        name: 日志记录器名称, 默认为None使用调用者的模块名

    Returns:
        配置好的logger实例
    """
    return logger.bind(name=name)
