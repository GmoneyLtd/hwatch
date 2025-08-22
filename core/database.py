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
        logger.info("Database initialization successful.")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
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
    Save task results to database.

    Args:
        task_alias (str): Task alias.
        device_name (str): Device name.
        results (Dict[str, Any]): Key-value pair results to save.
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
        logger.debug(f"Successfully saved {len(records)} records for task {task_alias} on {device_name}.")
        return True
    except Exception as e:
        logger.error(f"Failed to save task results to database (task: {task_alias}): {e}")
        return False


async def get_available_tasks(start_date: datetime, end_date: datetime) -> list[str]:
    """
    Get list of tasks that have data in the specified time range in the database.

    Args:
        start_date (datetime): Query start time
        end_date (datetime): Query end time

    Returns:
        List[str]: List of task aliases that contain data.
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
        logger.error(f"Failed to query available task list: {e}")
        return []


async def get_available_devices(start_date: datetime, end_date: datetime, task_alias: str | None = None) -> list[str]:
    """
    Get list of devices that have data in the specified time range in the database.

    Args:
        start_date (datetime): Query start time
        end_date (datetime): Query end time
        task_alias (str, optional): Specified task alias, if provided only return devices for that task

    Returns:
        List[str]: List of device names that contain data.
    """
    try:
        conn = await _get_connection()
        if task_alias:
            # If task is specified, only return devices for that task in the specified time range
            async with conn.execute(
                "SELECT DISTINCT device_name FROM task_results WHERE timestamp BETWEEN ? AND ? AND task_alias = ? ORDER BY device_name",
                (start_date, end_date, task_alias),
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            # If no task is specified, return all devices
            async with conn.execute(
                "SELECT DISTINCT device_name FROM task_results WHERE timestamp BETWEEN ? AND ? ORDER BY device_name",
                (start_date, end_date),
            ) as cursor:
                rows = await cursor.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"Failed to query available device list: {e}")
        return []


async def get_chart_data(task_alias: str, start_date: datetime, end_date: datetime) -> list[dict[str, Any]]:
    """
    Query time series data for chart display.

    Args:
        task_alias (str): Task alias to query.
        start_date (datetime): Query start time.
        end_date (datetime): Query end time.

    Returns:
        List[Dict[str, Any]]: List of dictionaries containing query results.
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
        logger.error(f"Failed to query chart data (task: {task_alias}): {e}")
        return []


# Database optimization and maintenance functions
async def optimize_database():
    """Optimize database, compress storage and rebuild indexes"""
    try:
        conn = await _get_connection()
        # Vacuum and analyze for better performance
        await conn.execute("VACUUM")
        await conn.execute("ANALYZE")
        await conn.commit()
        logger.info("Database optimization completed.")
        return True
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        return False


async def cleanup_old_data(days: int = 90):
    """Clean up old data from specified days ago"""
    try:
        conn = await _get_connection()
        # Delete data older than specified days
        cursor = await conn.execute(f"DELETE FROM task_results WHERE timestamp < datetime('now', '-{days} days')")
        deleted_count = cursor.rowcount
        await conn.commit()
        logger.info(f"Old data cleanup completed (deleted {deleted_count} records older than {days} days).")
        return True
    except Exception as e:
        logger.error(f"Old data cleanup failed: {e}")
        return False


async def get_database_stats():
    """Get database statistics for monitoring"""
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
        logger.error(f"Failed to get database statistics: {e}")
        return {}


async def close_db():
    """Close database connection"""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None
        logger.info("Database connection has been closed.")
