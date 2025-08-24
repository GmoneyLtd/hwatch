"""
Performance monitoring and diagnostic system
"""

import asyncio
import gc
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

import psutil
from loguru import logger


@dataclass
class PerformanceMetric:
    """Performance metric data point"""

    name: str
    value: float
    timestamp: datetime
    tags: dict[str, str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


class PerformanceMonitor:
    """System performance monitoring and diagnostics"""

    def __init__(self, max_metrics=10000):
        self.metrics = defaultdict(lambda: deque(maxlen=1000))
        self.max_metrics = max_metrics
        self.thresholds = {
            "task_execution_time": 30.0,  # seconds
            "memory_usage_mb": 500,
            "cpu_usage_percent": 80,
            "disk_usage_percent": 90,
            "database_query_time": 5.0,
            "file_write_time": 2.0,
        }
        self.alerts = []
        self.max_alerts = 100
        self.start_time = time.time()
        self.process = psutil.Process()

        # Performance counters
        self.counters = defaultdict(int)
        self.timers = {}

        # Background monitoring task
        self.monitoring_task = None
        self.monitoring_interval = 60  # seconds

    async def start_monitoring(self):
        """Start background performance monitoring"""
        if self.monitoring_task is None:
            self.monitoring_task = asyncio.create_task(self._background_monitor())
            logger.info("Performance monitoring started")

    async def stop_monitoring(self):
        """Stop background performance monitoring"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
            logger.info("Performance monitoring stopped")

    async def _background_monitor(self):
        """Background monitoring loop"""
        while True:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background monitoring error: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = self.process.cpu_percent()
            self.record_metric("cpu_usage_percent", cpu_percent)

            # Memory usage
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            self.record_metric("memory_usage_mb", memory_mb)

            # Disk usage
            disk_usage = psutil.disk_usage(".")
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            self.record_metric("disk_usage_percent", disk_percent)

            # File descriptors (Unix only)
            if hasattr(self.process, "num_fds"):
                fd_count = self.process.num_fds()
                self.record_metric("file_descriptors", fd_count)

            # Thread count
            thread_count = self.process.num_threads()
            self.record_metric("thread_count", thread_count)

            # Check thresholds and generate alerts
            self._check_thresholds()

        except Exception as e:
            logger.error(f"System metrics collection failed: {e}")

    def record_metric(self, name: str, value: float, tags: dict[str, str] | None = None):
        """Record a performance metric"""
        metric = PerformanceMetric(name=name, value=value, timestamp=datetime.now(), tags=tags or {})

        self.metrics[name].append(metric)

        # Check if this metric exceeds threshold
        if name in self.thresholds and value > self.thresholds[name]:
            self._generate_alert(name, value, self.thresholds[name])

    def increment_counter(self, name: str, value: int = 1):
        """Increment a performance counter"""
        self.counters[name] += value

    @asynccontextmanager
    async def measure_time(self, operation_name: str, tags: dict[str, str] | None = None):
        """Context manager to measure execution time"""
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            self.record_metric(f"{operation_name}_execution_time", execution_time, tags)

            # Check for slow operations
            threshold_key = f"{operation_name}_execution_time"
            if threshold_key in self.thresholds:
                if execution_time > self.thresholds[threshold_key]:
                    logger.warning(
                        f"Slow operation detected: {operation_name} took {execution_time:.2f}s",
                        extra={"operation": operation_name, "duration": execution_time, "tags": tags},
                    )

    def _generate_alert(self, metric_name: str, current_value: float, threshold: float):
        """Generate performance alert"""
        alert = {
            "timestamp": datetime.now(),
            "metric": metric_name,
            "value": current_value,
            "threshold": threshold,
            "severity": self._determine_alert_severity(metric_name, current_value, threshold),
        }

        self.alerts.append(alert)

        # Maintain alerts history
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts :]

        # Log alert
        logger.warning(f"Performance alert: {metric_name} = {current_value:.2f} (threshold: {threshold})", extra=alert)

    def _determine_alert_severity(self, metric_name: str, value: float, threshold: float) -> str:
        """Determine alert severity based on how much threshold is exceeded"""
        ratio = value / threshold

        if ratio > 2.0:
            return "critical"
        elif ratio > 1.5:
            return "high"
        elif ratio > 1.2:
            return "medium"
        else:
            return "low"

    def _check_thresholds(self):
        """Check all current metrics against thresholds"""
        for metric_name, threshold in self.thresholds.items():
            if metric_name in self.metrics:
                recent_metrics = list(self.metrics[metric_name])
                if recent_metrics:
                    latest_value = recent_metrics[-1].value
                    if latest_value > threshold:
                        self._generate_alert(metric_name, latest_value, threshold)

    def get_performance_summary(self) -> dict[str, Any]:
        """Get comprehensive performance summary"""
        summary = {
            "uptime_seconds": time.time() - self.start_time,
            "metrics_collected": sum(len(metrics) for metrics in self.metrics.values()),
            "active_alerts": len([a for a in self.alerts if (datetime.now() - a["timestamp"]).seconds < 3600]),
            "counters": dict(self.counters),
            "recent_metrics": {},
            "system_info": self._get_system_info(),
            "memory_info": self._get_memory_info(),
            "performance_trends": self._get_performance_trends(),
        }

        # Add recent metrics (last 10 values for each metric)
        for metric_name, metric_deque in self.metrics.items():
            recent_values = [m.value for m in list(metric_deque)[-10:]]
            if recent_values:
                summary["recent_metrics"][metric_name] = {
                    "current": recent_values[-1],
                    "average": sum(recent_values) / len(recent_values),
                    "min": min(recent_values),
                    "max": max(recent_values),
                    "count": len(recent_values),
                }

        return summary

    def _get_system_info(self) -> dict[str, Any]:
        """Get system information"""
        try:
            return {
                "cpu_count": psutil.cpu_count(),
                "memory_total_mb": psutil.virtual_memory().total / 1024 / 1024,
                "disk_total_gb": psutil.disk_usage(".").total / 1024 / 1024 / 1024,
                "platform": os.name,
                "python_version": f"{psutil.version_info}",
                "process_id": os.getpid(),
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {}

    def _get_memory_info(self) -> dict[str, Any]:
        """Get detailed memory information"""
        try:
            memory_info = self.process.memory_info()
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": self.process.memory_percent(),
                "gc_stats": {"collections": gc.get_stats(), "objects": len(gc.get_objects())},
            }
        except Exception as e:
            logger.error(f"Failed to get memory info: {e}")
            return {}

    def _get_performance_trends(self) -> dict[str, Any]:
        """Get performance trends over time"""
        trends = {}

        for metric_name, metric_deque in self.metrics.items():
            if len(metric_deque) < 2:
                continue

            values = [m.value for m in metric_deque]
            timestamps = [m.timestamp for m in metric_deque]

            # Calculate trend (simple linear regression slope)
            if len(values) >= 5:
                n = len(values)
                x_vals = list(range(n))
                x_mean = sum(x_vals) / n
                y_mean = sum(values) / n

                numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, values, strict=False))
                denominator = sum((x - x_mean) ** 2 for x in x_vals)

                if denominator != 0:
                    slope = numerator / denominator
                    trends[metric_name] = {
                        "trend": "increasing" if slope > 0.1 else "decreasing" if slope < -0.1 else "stable",
                        "slope": slope,
                        "data_points": n,
                        "time_span_minutes": (timestamps[-1] - timestamps[0]).total_seconds() / 60,
                    }

        return trends

    def get_alerts(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get alerts from the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alerts if alert["timestamp"] > cutoff_time]

    def clear_alerts(self):
        """Clear all alerts"""
        self.alerts.clear()
        logger.info("Performance alerts cleared")

    def force_gc(self):
        """Force garbage collection and record metrics"""
        before_objects = len(gc.get_objects())
        collected = gc.collect()
        after_objects = len(gc.get_objects())

        self.record_metric("gc_collected_objects", collected)
        self.record_metric("gc_total_objects", after_objects)

        logger.info(f"Forced GC: collected {collected} objects, {before_objects} -> {after_objects}")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
