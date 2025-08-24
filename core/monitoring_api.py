"""
Monitoring API endpoints for performance and error tracking
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from loguru import logger

from core.error_handler import error_handler
from core.performance_monitor import performance_monitor

# Create monitoring router
monitoring_router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


def get_current_user():
    """Simple authentication placeholder"""
    return {"user": "admin"}


@monitoring_router.get("/health")
async def health_check():
    """Health check endpoint (no authentication required)"""
    try:
        return {"status": "healthy", "timestamp": datetime.now().isoformat(), "version": "2.0.0"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed") from e


@monitoring_router.get("/performance")
async def get_performance_metrics():
    """Get comprehensive performance metrics"""
    try:
        # Authentication check (user variable not used in this endpoint)
        get_current_user()
        metrics = performance_monitor.get_performance_summary()
        return {"metrics": metrics, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics") from e


@monitoring_router.get("/errors")
async def get_error_statistics():
    """Get error statistics and analysis"""
    try:
        # Authentication check
        get_current_user()
        error_stats = error_handler.get_error_summary()
        return {"error_statistics": error_stats, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Failed to get error statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve error statistics") from e


@monitoring_router.get("/alerts")
async def get_alerts(hours: int = 24):
    """Get performance alerts from the last N hours"""
    try:
        # Authentication check
        get_current_user()
        alerts = performance_monitor.get_alerts(hours)
        return {"alerts": alerts, "hours": hours, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts") from e


@monitoring_router.post("/alerts/clear")
async def clear_alerts():
    """Clear all performance alerts"""
    try:
        # Authentication check
        get_current_user()
        cleared_count = performance_monitor.clear_alerts()
        return {
            "message": "Alerts cleared successfully",
            "cleared_count": cleared_count,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to clear alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear alerts") from e


@monitoring_router.post("/gc")
async def force_garbage_collection():
    """Force garbage collection and return memory statistics"""
    try:
        # Authentication check
        get_current_user()
        import gc

        import psutil

        # Get memory before GC
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Force garbage collection
        collected = gc.collect()

        # Get memory after GC
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_freed = memory_before - memory_after

        return {
            "message": "Garbage collection completed",
            "objects_collected": collected,
            "memory_before_mb": round(memory_before, 2),
            "memory_after_mb": round(memory_after, 2),
            "memory_freed_mb": round(memory_freed, 2),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to force garbage collection: {e}")
        raise HTTPException(status_code=500, detail="Failed to force garbage collection") from e


@monitoring_router.get("/system")
async def get_system_info():
    """Get system information and resource usage"""
    try:
        # Authentication check
        get_current_user()
        system_info = performance_monitor.get_system_info()
        return {"system_info": system_info, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system information") from e


@monitoring_router.get("/metrics/export")
async def export_metrics(format: str = "json"):
    """Export metrics in various formats"""
    try:
        # Authentication check
        get_current_user()

        if format.lower() == "json":
            metrics = {
                "performance": performance_monitor.get_performance_summary(),
                "errors": error_handler.get_error_summary(),
                "system": performance_monitor.get_system_info(),
                "export_time": datetime.now().isoformat(),
                "format": "json",
            }
            return metrics

        elif format.lower() == "prometheus":
            # Generate Prometheus format
            lines = []

            # Performance metrics
            perf_summary = performance_monitor.get_performance_summary()
            for metric_name, value in perf_summary.items():
                if isinstance(value, int | float):
                    lines.append(f"hwatch_{metric_name} {value}")

            # Error metrics
            error_summary = error_handler.get_error_summary()
            lines.append(f"hwatch_total_errors {error_summary.get('total_errors', 0)}")
            lines.append(f"hwatch_recent_errors {error_summary.get('recent_errors', 0)}")

            prometheus_output = "\n".join(lines)
            return {"metrics": prometheus_output, "format": "prometheus", "export_time": datetime.now().isoformat()}
        else:
            raise HTTPException(status_code=400, detail="Unsupported format. Use 'json' or 'prometheus'")

    except Exception as e:
        logger.error(f"Failed to export metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to export metrics") from e
