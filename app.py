import argparse
import asyncio
import os

import uvicorn
from loguru import logger

from core.config_loader import AppConfig, load_config
from core.database import close_db, init_db
from core.scheduler import TaskScheduler

# 导入核心模块
from core.ulog import setup_logging
from core.watch import start_watching
from core.web_server import app, app_state

# --- 全局变量 ---
CONFIG_PATH = "config.yaml"


# --- 主应用逻辑 ---
def reload_config_and_reschedule(scheduler: TaskScheduler):
    """回调函数: 重新加载配置并增量更新调度器。"""
    logger.info("检测到配置变更, 开始重载...")
    new_config = load_config(CONFIG_PATH)
    if new_config:
        # 更新Web服务器持有的配置
        app_state["config"] = new_config

        # 使用增量更新机制
        scheduler.reload_config_and_update_tasks(new_config)
        logger.success("配置重载和任务增量更新成功! ")
    else:
        logger.error("加载新配置失败, 调度器将继续使用旧配置运行。")


async def main():
    """应用主入口。"""
    # 1. 解析命令行参数
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    parser = argparse.ArgumentParser(description="Hwatch - 轻量级运维采集平台")
    parser.add_argument(
        "--level",
        default="WARNING",  # 命令行参数的默认值
        choices=valid_levels,
        help="设置控制台的日志级别",
    )
    args = parser.parse_args()

    # 2. 检查环境变量, 环境变量优先级最高
    env_log_level = os.getenv("LOG_LEVEL")
    if env_log_level:
        env_log_level = env_log_level.upper()
        if env_log_level in valid_levels:
            final_log_level = env_log_level
            log_source = "环境变量"
        else:
            logger.warning(f"环境变量LOG_LEVEL值无效: {env_log_level}, 使用命令行参数: {args.level}")
            final_log_level = args.level
            log_source = "命令行参数(环境变量无效)"
    else:
        final_log_level = args.level
        log_source = "命令行参数"

    # 3. 初始化日志系统
    setup_logging(level=final_log_level)
    logger.info(f"日志级别设置为: {final_log_level} (来源: {log_source})")

    # 4. 初始化数据库
    await init_db()

    # 5. 加载初始配置
    config = load_config(CONFIG_PATH)
    if not config:
        logger.error(f"无法加载初始配置 {CONFIG_PATH}, 程序退出。")
        return

    # 6. 初始化调度器
    scheduler = TaskScheduler(config)

    # 7. 设置Web应用状态机
    app_state["config"] = config
    app_state["config_path"] = CONFIG_PATH
    app_state["scheduler"] = scheduler
    app_state["reload_callback"] = lambda: reload_config_and_reschedule(scheduler)

    # 8. 首次调度所有任务
    scheduler.schedule_all_tasks()

    # 9. 启动文件监控
    start_watching(CONFIG_PATH, app_state["reload_callback"])

    # 10. 启动调度器
    scheduler.start()

    # 11. 配置并启动Uvicorn Web服务器
    uvicorn_config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level=args.level.lower())
    server = uvicorn.Server(uvicorn_config)

    logger.info("Hwatch 应用启动成功! 访问 http://localhost:8080")

    try:
        await server.serve()
    finally:
        # 优雅关闭
        scheduler.stop()
        await close_db()
        logger.info("Hwatch 应用已关闭。")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("收到退出信号, 程序正在关闭...")
