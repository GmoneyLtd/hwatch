import asyncio
import time
from collections.abc import Callable
from typing import Any

from loguru import logger


class ConnectionStatusCache:
    """连接状态缓存, 减少不必要的连接检查"""

    def __init__(self, cache_ttl: float = 30.0):
        self.cache: dict[str, tuple[float, bool]] = {}
        self.cache_ttl = cache_ttl
        self.cleanup_interval = 300  # 5分钟清理一次过期缓存
        self.last_cleanup = time.time()

    async def is_valid_cached(self, pool_key: str, conn: Any, check_func: Callable) -> bool:
        """检查连接是否有效, 使用缓存优化"""
        current_time = time.time()

        # 定期清理过期缓存
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_expired_cache(current_time)

        # 检查缓存
        if pool_key in self.cache:
            last_check, status = self.cache[pool_key]
            if current_time - last_check < self.cache_ttl and status:
                logger.debug(f"Connection status cache hit for {pool_key}")
                return True

        # 执行实际检查
        try:
            status = await check_func(conn)
            self.cache[pool_key] = (current_time, status)
            logger.debug(f"Connection status checked and cached for {pool_key}: {status}")
            return status
        except Exception as e:
            logger.debug(f"Connection check failed for {pool_key}: {e}")
            self.cache[pool_key] = (current_time, False)
            return False

    def _cleanup_expired_cache(self, current_time: float):
        """清理过期的缓存条目"""
        expired_keys = []
        for key, (last_check, _) in self.cache.items():
            if current_time - last_check > self.cache_ttl * 2:  # 保留时间是TTL的2倍
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired connection cache entries")

        self.last_cleanup = current_time

    def invalidate(self, pool_key: str):
        """使指定连接的缓存失效"""
        if pool_key in self.cache:
            del self.cache[pool_key]
            logger.debug(f"Invalidated connection cache for {pool_key}")

    def clear_all(self):
        """清空所有缓存"""
        self.cache.clear()
        logger.debug("Cleared all connection cache")


# 全局连接状态缓存实例
_connection_cache: ConnectionStatusCache | None = None


def get_connection_cache() -> ConnectionStatusCache:
    """获取全局连接状态缓存实例"""
    global _connection_cache
    if _connection_cache is None:
        _connection_cache = ConnectionStatusCache()
    return _connection_cache
