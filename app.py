
import argparse
import asyncio

import uvicorn
from loguru import logger

from core.config_loader import AppConfig, load_config
from core.database import init_db
from core.scheduler import TaskScheduler

# 导入核心模块
from core.ulog import setup_logging
from core.watch import start_watching
from core.web_server import app, app_state

# --- 全局变量 ---
CONFIG_PATH = "config.yaml"

# --- 主应用逻辑 ---
def reload_config_and_reschedule(scheduler: TaskScheduler):
    """回调函数: 重新加载配置并更新调度器。"""
    logger.info("检测到配置变更, 开始重载...")
    new_config = load_config(CONFIG_PATH)
    if new_config:
        # 更新Web服务器和调度器持有的配置
        app_state["config"] = new_config
        scheduler.config = new_config
        scheduler.device_map = {device.name: device for device in new_config.devices}
        scheduler.schedule_all_tasks()
        logger.success("配置重载和任务重新调度成功! ")
    else:
        logger.error("加载新配置失败, 调度器将继续使用旧配置运行。")

async def main():
    """应用主入口。"""
    # 1. 解析命令行参数
    parser = argparse.ArgumentParser(description="Hwatch - 轻量级运维采集平台")
    parser.add_argument(
        "--level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="设置控制台的日志级别。"
    )
    args = parser.parse_args()

    # 2. 初始化日志系统
    setup_logging(level=args.level)

    # 3. 初始化数据库
    await init_db()

    # 4. 加载初始配置
    config = load_config(CONFIG_PATH)
    if not config:
        logger.error(f"无法加载初始配置 {CONFIG_PATH}, 程序退出。")
        return

    # 5. 初始化调度器
    scheduler = TaskScheduler(config)

    # 6. 设置Web应用状态机
    app_state["config"] = config
    app_state["config_path"] = CONFIG_PATH
    app_state["scheduler"] = scheduler
    app_state["reload_callback"] = lambda: reload_config_and_reschedule(scheduler)

    # 7. 首次调度所有任务
    scheduler.schedule_all_tasks()

    # 8. 启动文件监控
    start_watching(CONFIG_PATH, app_state["reload_callback"])

    # 9. 启动调度器
    scheduler.start()

    # 10. 配置并启动Uvicorn Web服务器
    uvicorn_config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level=args.level.lower())
    server = uvicorn.Server(uvicorn_config)
    
    logger.info("Hwatch 应用启动成功! 访问 http://localhost:8080")
    
    try:
        await server.serve()
    finally:
        # 优雅关闭
        scheduler.stop()
        logger.info("Hwatch 应用已关闭。")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("收到退出信号, 程序正在关闭...")
