from datetime import datetime, timedelta
from typing import Any

import aiosqlite
from loguru import logger

DB_FILE = "hwatch.db"


async def init_db():
    """初始化数据库, 创建必要的表。"""
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS task_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                task_alias TEXT NOT NULL,
                device_name TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT
            )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_task_alias ON task_results (task_alias)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON task_results (timestamp)")
            await db.commit()
        logger.info("数据库初始化成功。")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")


async def save_result(task_alias: str, device_name: str, results: dict[str, Any]):
    """
    将任务结果保存到数据库。

    Args:
        task_alias (str): 任务的别名。
        device_name (str): 设备的名称。
        results (Dict[str, Any]): 要保存的键值对结果。
    """
    timestamp = datetime.now()
    records = [(timestamp, task_alias, device_name, key, str(value)) for key, value in results.items()]

    try:
        async with aiosqlite.connect(DB_FILE) as db:
            await db.executemany(
                "INSERT INTO task_results (timestamp, task_alias, device_name, key, value) VALUES (?, ?, ?, ?, ?)",
                records,
            )
            await db.commit()
        logger.debug(f"成功为任务 {task_alias} on {device_name} 保存 {len(records)} 条记录。")
    except Exception as e:
        logger.error(f"保存任务结果到数据库失败 (任务: {task_alias}): {e}")


async def get_available_tasks(start_date: datetime, end_date: datetime) -> list[str]:
    """
    获取数据库中指定时间区间内有数据的任务列表。

    Args:
        start_date (datetime): 查询开始时间
        end_date (datetime): 查询结束时间

    Returns:
        List[str]: 包含数据的任务别名列表。
    """
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            cursor = await db.execute(
                "SELECT DISTINCT task_alias FROM task_results WHERE timestamp BETWEEN ? AND ? ORDER BY task_alias",
                (start_date, end_date),
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"查询可用任务列表失败: {e}")
        return []


async def get_available_devices(start_date: datetime, end_date: datetime, task_alias: str = None) -> list[str]:
    """
    获取数据库中指定时间区间内有数据的设备列表。

    Args:
        start_date (datetime): 查询开始时间
        end_date (datetime): 查询结束时间
        task_alias (str, optional): 指定任务别名，如果提供则只返回该任务的设备

    Returns:
        List[str]: 包含数据的设备名称列表。
    """
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            if task_alias:
                # 如果指定了任务，只返回该任务在指定时间区间内的设备
                cursor = await db.execute(
                    "SELECT DISTINCT device_name FROM task_results WHERE timestamp BETWEEN ? AND ? AND task_alias = ? ORDER BY device_name",
                    (start_date, end_date, task_alias),
                )
            else:
                # 如果没有指定任务，返回所有设备
                cursor = await db.execute(
                    "SELECT DISTINCT device_name FROM task_results WHERE timestamp BETWEEN ? AND ? ORDER BY device_name",
                    (start_date, end_date),
                )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"查询可用设备列表失败: {e}")
        return []


async def get_chart_data(task_alias: str, start_date: datetime, end_date: datetime) -> list[dict[str, Any]]:
    """
    查询用于图表展示的时间序列数据。

    Args:
        task_alias (str): 要查询的任务别名。
        start_date (datetime): 查询的开始时间。
        end_date (datetime): 查询的结束时间。

    Returns:
        List[Dict[str, Any]]: 包含查询结果的字典列表。
    """
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT timestamp, device_name, key, value FROM task_results WHERE task_alias = ? AND timestamp BETWEEN ? AND ? ORDER BY timestamp ASC",
                (task_alias, start_date, end_date),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"查询图表数据失败 (任务: {task_alias}): {e}")
        return []
