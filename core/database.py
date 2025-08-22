from datetime import datetime, timedelta
from typing import Any

import aiosqlite
from loguru import logger

DB_FILE = "hwatch.db"

# Global async database connection
_db_connection: aiosqlite.Connection | None = None


async def init_db():
    """Initialize database with global connection and performance optimizations."""
    global _db_connection
    try:
        _db_connection = await aiosqlite.connect(DB_FILE)

        # Enable WAL mode for better concurrency
        await _db_connection.execute("PRAGMA journal_mode=WAL")
        await _db_connection.execute("PRAGMA synchronous=NORMAL")
        await _db_connection.execute("PRAGMA cache_size=10000")
        await _db_connection.execute("PRAGMA temp_store=memory")

        # Create table structure
        await _db_connection.execute("""
        CREATE TABLE IF NOT EXISTS task_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            task_alias TEXT NOT NULL,
            device_name TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT
        )
        """)

        # Create indexes for better query performance
        await _db_connection.execute("CREATE INDEX IF NOT EXISTS idx_task_alias ON task_results (task_alias)")
        await _db_connection.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON task_results (timestamp)")
        await _db_connection.execute("CREATE INDEX IF NOT EXISTS idx_device_name ON task_results (device_name)")
        await _db_connection.execute("CREATE INDEX IF NOT EXISTS idx_composite ON task_results (task_alias, timestamp)")

        await _db_connection.commit()
        logger.info("数据库初始化成功。")
        return True
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        # Clean up connection on error
        if _db_connection:
            await _db_connection.close()
            _db_connection = None
        return False


async def _get_connection() -> aiosqlite.Connection:
    """Get global database connection, initialize if needed."""
    global _db_connection
    if _db_connection is None:
        await init_db()
    if _db_connection is None:
        raise RuntimeError("Failed to initialize database connection")
    return _db_connection


async def save_result(task_alias: str, device_name: str, results: dict[str, Any]):
    """
    将任务结果保存到数据库。

    Args:
        task_alias (str): 任务的别名。
        device_name (str): 设备的名称。
        results (Dict[str, Any]): 要保存的键值对结果。
    """
    try:
        conn = await _get_connection()
        timestamp = datetime.now()

        # Prepare records for batch insert
        records = [(timestamp, task_alias, device_name, key, str(value)) for key, value in results.items()]

        # Batch insert using executemany for better performance
        await conn.executemany(
            "INSERT INTO task_results (timestamp, task_alias, device_name, key, value) VALUES (?, ?, ?, ?, ?)",
            records,
        )
        await conn.commit()
        logger.debug(f"成功为任务 {task_alias} on {device_name} 保存 {len(records)} 条记录。")
        return True
    except Exception as e:
        logger.error(f"保存任务结果到数据库失败 (任务: {task_alias}): {e}")
        return False


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
        conn = await _get_connection()
        async with conn.execute(
            "SELECT DISTINCT task_alias FROM task_results WHERE timestamp BETWEEN ? AND ? ORDER BY task_alias",
            (start_date, end_date),
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"查询可用任务列表失败: {e}")
        return []


async def get_available_devices(start_date: datetime, end_date: datetime, task_alias: str | None = None) -> list[str]:
    """
    获取数据库中指定时间区间内有数据的设备列表。

    Args:
        start_date (datetime): 查询开始时间
        end_date (datetime): 查询结束时间
        task_alias (str, optional): 指定任务别名, 如果提供则只返回该任务的设备

    Returns:
        List[str]: 包含数据的设备名称列表。
    """
    try:
        conn = await _get_connection()
        if task_alias:
            # 如果指定了任务, 只返回该任务在指定时间区间内的设备
            async with conn.execute(
                "SELECT DISTINCT device_name FROM task_results WHERE timestamp BETWEEN ? AND ? AND task_alias = ? ORDER BY device_name",
                (start_date, end_date, task_alias),
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            # 如果没有指定任务, 返回所有设备
            async with conn.execute(
                "SELECT DISTINCT device_name FROM task_results WHERE timestamp BETWEEN ? AND ? ORDER BY device_name",
                (start_date, end_date),
            ) as cursor:
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
        conn = await _get_connection()
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT timestamp, device_name, key, value FROM task_results WHERE task_alias = ? AND timestamp BETWEEN ? AND ? ORDER BY timestamp ASC",
            (task_alias, start_date, end_date),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"查询图表数据失败 (任务: {task_alias}): {e}")
        return []


# Database optimization and maintenance functions
async def optimize_database():
    """优化数据库, 压缩存储和重建索引"""
    try:
        conn = await _get_connection()
        # Vacuum and analyze for better performance
        await conn.execute("VACUUM")
        await conn.execute("ANALYZE")
        await conn.commit()
        logger.info("数据库优化完成。")
        return True
    except Exception as e:
        logger.error(f"数据库优化失败: {e}")
        return False


async def cleanup_old_data(days: int = 90):
    """清理指定天数之前的旧数据"""
    try:
        conn = await _get_connection()
        # Delete data older than specified days
        cursor = await conn.execute(f"DELETE FROM task_results WHERE timestamp < datetime('now', '-{days} days')")
        deleted_count = cursor.rowcount
        await conn.commit()
        logger.info(f"旧数据清理完成 (删除了 {deleted_count} 条超过 {days} 天的记录)。")
        return True
    except Exception as e:
        logger.error(f"旧数据清理失败: {e}")
        return False


async def get_database_stats():
    """获取数据库统计信息用于监控"""
    try:
        conn = await _get_connection()

        # Get table statistics
        async with conn.execute("SELECT COUNT(*) FROM task_results") as cursor:
            row = await cursor.fetchone()
            total_records = row[0] if row else 0

        async with conn.execute("SELECT COUNT(DISTINCT task_alias) FROM task_results") as cursor:
            row = await cursor.fetchone()
            unique_tasks = row[0] if row else 0

        async with conn.execute("SELECT COUNT(DISTINCT device_name) FROM task_results") as cursor:
            row = await cursor.fetchone()
            unique_devices = row[0] if row else 0

        # Get oldest and newest records
        async with conn.execute("SELECT MIN(timestamp), MAX(timestamp) FROM task_results") as cursor:
            row = await cursor.fetchone()
            min_time, max_time = (row[0], row[1]) if row else (None, None)

        return {
            "total_records": total_records,
            "unique_tasks": unique_tasks,
            "unique_devices": unique_devices,
            "oldest_record": min_time,
            "newest_record": max_time,
            "database_file": DB_FILE,
        }
    except Exception as e:
        logger.error(f"获取数据库统计信息失败: {e}")
        return {}


async def close_db():
    """关闭数据库连接"""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None
        logger.info("数据库连接已关闭。")
