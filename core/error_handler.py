"""
Enhanced error handling and classification system
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from loguru import logger


class ErrorType(Enum):
    """Error type classification"""

    NETWORK_ERROR = "network"
    TIMEOUT_ERROR = "timeout"
    AUTH_ERROR = "authentication"
    CONFIG_ERROR = "configuration"
    DATABASE_ERROR = "database"
    FILE_IO_ERROR = "file_io"
    SYSTEM_ERROR = "system"
    UNKNOWN_ERROR = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskError:
    """Structured error information"""

    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    device: str
    task: str
    timestamp: datetime
    exception: Exception | None = None
    recoverable: bool = True
    retry_count: int = 0
    context: dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}


class ErrorHandler:
    """Enhanced error handler with recovery strategies"""

    def __init__(self):
        self.error_stats = defaultdict(int)
        self.error_history = []
        self.max_history = 1000
        self.recovery_strategies = {
            ErrorType.NETWORK_ERROR: self._handle_network_error,
            ErrorType.TIMEOUT_ERROR: self._handle_timeout_error,
            ErrorType.AUTH_ERROR: self._handle_auth_error,
            ErrorType.DATABASE_ERROR: self._handle_database_error,
            ErrorType.FILE_IO_ERROR: self._handle_file_io_error,
        }
        self.circuit_breakers = {}  # Device-based circuit breakers

    def classify_error(self, exception: Exception, context: dict[str, Any] | None = None) -> ErrorType:
        """Classify error based on exception type and context"""
        if context is None:
            context = {}

        error_msg = str(exception).lower()

        # Network related errors
        if any(keyword in error_msg for keyword in ["connection", "network", "unreachable", "refused", "reset"]):
            return ErrorType.NETWORK_ERROR

        # Timeout errors
        if any(keyword in error_msg for keyword in ["timeout", "timed out", "deadline exceeded"]):
            return ErrorType.TIMEOUT_ERROR

        # Authentication errors
        if any(keyword in error_msg for keyword in ["authentication", "permission", "unauthorized", "access denied"]):
            return ErrorType.AUTH_ERROR

        # Database errors
        if any(keyword in error_msg for keyword in ["database", "sqlite", "sql", "constraint", "integrity"]):
            return ErrorType.DATABASE_ERROR

        # File I/O errors
        if any(keyword in error_msg for keyword in ["file", "directory", "permission denied", "no such file"]):
            return ErrorType.FILE_IO_ERROR

        # Configuration errors
        if any(keyword in error_msg for keyword in ["config", "yaml", "validation", "missing"]):
            return ErrorType.CONFIG_ERROR

        return ErrorType.UNKNOWN_ERROR

    def determine_severity(self, error_type: ErrorType, device: str, task: str) -> ErrorSeverity:
        """Determine error severity based on type and frequency"""
        # Check error frequency for this device
        device_errors = sum(
            1 for err in self.error_history[-100:] if err.device == device and err.error_type == error_type
        )

        # Critical errors
        if error_type in [ErrorType.DATABASE_ERROR, ErrorType.CONFIG_ERROR]:
            return ErrorSeverity.CRITICAL

        # High severity for frequent errors
        if device_errors > 5:
            return ErrorSeverity.HIGH

        # Medium severity for auth and network issues
        if error_type in [ErrorType.AUTH_ERROR, ErrorType.NETWORK_ERROR]:
            return ErrorSeverity.MEDIUM

        return ErrorSeverity.LOW

    async def handle_error(
        self, exception: Exception, device: str, task: str, context: dict[str, Any] | None = None
    ) -> bool:
        """Handle error and return whether to retry"""
        if context is None:
            context = {}

        error_type = self.classify_error(exception, context)
        severity = self.determine_severity(error_type, device, task)

        task_error = TaskError(
            error_type=error_type,
            severity=severity,
            message=str(exception),
            device=device,
            task=task,
            timestamp=datetime.now(),
            exception=exception,
            context=context,
        )

        # Update statistics
        self.error_stats[error_type] += 1
        self.error_history.append(task_error)

        # Maintain history size
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history :]

        # Log structured error
        self._log_structured_error(task_error)

        # Check circuit breaker
        if self._should_circuit_break(device, error_type):
            logger.warning(f"Circuit breaker activated for device {device}")
            return False

        # Execute recovery strategy
        if error_type in self.recovery_strategies:
            return await self.recovery_strategies[error_type](task_error)

        return task_error.recoverable and task_error.retry_count < 3

    def _log_structured_error(self, error: TaskError):
        """Log error with structured information"""
        log_data = {
            "error_type": error.error_type.value,
            "severity": error.severity.value,
            "device": error.device,
            "task": error.task,
            "message": error.message,
            "retry_count": error.retry_count,
            "timestamp": error.timestamp.isoformat(),
        }

        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical("Critical task error", extra=log_data)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error("High severity task error", extra=log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning("Medium severity task error", extra=log_data)
        else:
            logger.info("Low severity task error", extra=log_data)

    def _should_circuit_break(self, device: str, error_type: ErrorType) -> bool:
        """Check if circuit breaker should activate"""
        if device not in self.circuit_breakers:
            self.circuit_breakers[device] = {
                "failure_count": 0,
                "last_failure": None,
                "state": "closed",  # closed, open, half-open
            }

        breaker = self.circuit_breakers[device]
        current_time = time.time()

        # Reset if enough time has passed
        if breaker["last_failure"] and current_time - breaker["last_failure"] > 300:  # 5 minutes
            breaker["failure_count"] = 0
            breaker["state"] = "closed"

        # Increment failure count for critical errors
        if error_type in [ErrorType.NETWORK_ERROR, ErrorType.AUTH_ERROR]:
            breaker["failure_count"] += 1
            breaker["last_failure"] = current_time

        # Open circuit if too many failures
        if breaker["failure_count"] >= 5:
            breaker["state"] = "open"
            return True

        return breaker["state"] == "open"

    async def _handle_network_error(self, error: TaskError) -> bool:
        """Handle network errors with exponential backoff"""
        backoff_time = min(2**error.retry_count, 60)  # Max 60 seconds
        logger.info(f"Network error for {error.device}, backing off {backoff_time}s")
        await asyncio.sleep(backoff_time)
        return error.retry_count < 3

    async def _handle_timeout_error(self, error: TaskError) -> bool:
        """Handle timeout errors"""
        if error.retry_count < 2:
            logger.info(f"Timeout error for {error.device}, retrying with longer timeout")
            return True
        return False

    async def _handle_auth_error(self, error: TaskError) -> bool:
        """Handle authentication errors"""
        logger.warning(f"Authentication error for {error.device}, check credentials")
        return False  # Don't retry auth errors

    async def _handle_database_error(self, error: TaskError) -> bool:
        """Handle database errors"""
        logger.error(f"Database error: {error.message}")
        await asyncio.sleep(1)  # Brief pause before retry
        return error.retry_count < 2

    async def _handle_file_io_error(self, error: TaskError) -> bool:
        """Handle file I/O errors"""
        logger.warning(f"File I/O error: {error.message}")
        await asyncio.sleep(0.5)
        return error.retry_count < 2

    def get_error_summary(self) -> dict[str, Any]:
        """Get error statistics summary"""
        recent_errors = [
            err for err in self.error_history if (datetime.now() - err.timestamp).seconds < 3600
        ]  # Last hour

        return {
            "total_errors": len(self.error_history),
            "recent_errors": len(recent_errors),
            "error_types": dict(self.error_stats),
            "circuit_breakers": {device: breaker["state"] for device, breaker in self.circuit_breakers.items()},
            "top_error_devices": self._get_top_error_devices(),
            "error_trend": self._get_error_trend(),
        }

    def _get_top_error_devices(self) -> list[dict[str, Any]]:
        """Get devices with most errors"""
        device_errors = defaultdict(int)
        for error in self.error_history[-100:]:  # Recent errors
            device_errors[error.device] += 1

        return [
            {"device": device, "error_count": count}
            for device, count in sorted(device_errors.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

    def _get_error_trend(self) -> list[dict[str, Any]]:
        """Get error trend over time"""
        now = datetime.now()
        hourly_errors = defaultdict(int)

        for error in self.error_history:
            hours_ago = int((now - error.timestamp).total_seconds() / 3600)
            if hours_ago < 24:  # Last 24 hours
                hourly_errors[hours_ago] += 1

        return [{"hours_ago": hours, "error_count": count} for hours, count in sorted(hourly_errors.items())]


# Global error handler instance
error_handler = ErrorHandler()
