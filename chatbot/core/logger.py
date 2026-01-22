"""Structured logging utilities for consistent logging across the application."""
import logging
import sys
from typing import Optional, Dict, Any
from datetime import datetime
from functools import wraps
import json


class StructuredLogger:
    """Logger with structured logging support and consistent formatting."""

    _instances: Dict[str, 'StructuredLogger'] = {}

    def __init__(self, name: str = "chatbot", level: str = "INFO"):
        """Initialize structured logger.
        
        Args:
            name: Logger name
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self._setup_handler(level)
    
    def _setup_handler(self, level: str) -> None:
        """Setup logger with console handler."""
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        # Prevent propagation to root logger (avoids duplicate logs)
        self.logger.propagate = False

        # Avoid adding handlers if already configured
        if self.logger.handlers:
            return

        # Console handler with structured format
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level.upper(), logging.INFO))

        # Structured format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    @classmethod
    def get_instance(cls, name: str = "chatbot") -> 'StructuredLogger':
        """Get or create singleton instance for given name."""
        if name not in cls._instances:
            cls._instances[name] = cls(name)
        return cls._instances[name]
    
    def set_level(self, level: str) -> None:
        """Set logging level.
        
        Args:
            level: Level name (DEBUG, INFO, WARNING, ERROR)
        """
        lvl = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(lvl)
        for handler in self.logger.handlers:
            handler.setLevel(lvl)
    
    def debug(self, msg: str, **kwargs) -> None:
        """Log debug message with structured data."""
        extra = self._prepare_extra(kwargs)
        self.logger.debug(msg, extra=extra)
    
    def info(self, msg: str, **kwargs) -> None:
        """Log info message with structured data."""
        extra = self._prepare_extra(kwargs)
        self.logger.info(msg, extra=extra)
    
    def warning(self, msg: str, **kwargs) -> None:
        """Log warning message with structured data."""
        extra = self._prepare_extra(kwargs)
        self.logger.warning(msg, extra=extra)
    
    def error(self, msg: str, **kwargs) -> None:
        """Log error message with structured data."""
        extra = self._prepare_extra(kwargs)
        self.logger.error(msg, extra=extra)
    
    def exception(self, msg: str, exc: Exception = None, **kwargs) -> None:
        """Log exception with traceback."""
        extra = self._prepare_extra(kwargs)
        if exc:
            extra['exception'] = str(exc)
        self.logger.exception(msg, extra=extra)
    
    def _prepare_extra(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare extra dict for logging."""
        extra = kwargs.copy()
        extra['timestamp'] = datetime.now().isoformat()
        return extra
    
    def log_performance(self, operation: str, duration: float, **kwargs) -> None:
        """Log performance metric.
        
        Args:
            operation: Name of operation
            duration: Duration in seconds
            **kwargs: Additional metrics
        """
        self.info(f"Performance: {operation}", 
                  operation=operation, 
                  duration_seconds=duration,
                  **kwargs)
    
    def log_api_call(self, endpoint: str, status_code: int, duration: float = None) -> None:
        """Log API call.
        
        Args:
            endpoint: API endpoint
            status_code: HTTP status code
            duration: Optional request duration
        """
        self.info(f"API call to {endpoint}", 
                  endpoint=endpoint, 
                  status_code=status_code,
                  duration_seconds=duration)


def get_logger(name: str = "chatbot") -> StructuredLogger:
    """Get structured logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger.get_instance(name)


# Backward compatibility - returns standard logger
def get_compat_logger(name: str = "chatbot") -> logging.Logger:
    """Get standard logger for backward compatibility."""
    return logging.getLogger(name)


# Context manager for timing and logging
class log_performance:
    """Context manager to log performance of code blocks."""
    
    def __init__(self, operation: str, logger: Optional[StructuredLogger] = None):
        """Initialize.
        
        Args:
            operation: Name of operation to log
            logger: Optional logger instance
        """
        self.operation = operation
        self.logger = logger or get_logger()
        self.start_time: float = 0
    
    def __enter__(self) -> 'log_performance':
        """Enter context."""
        import time
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and log duration."""
        import time
        duration = time.perf_counter() - self.start_time
        self.logger.log_performance(self.operation, duration)
        
        if exc_type:
            self.logger.error(f"Operation {self.operation} failed", 
                            exception=str(exc_val))


def logged_function(operation: str = None):
    """Decorator to log function execution.
    
    Args:
        operation: Optional operation name (defaults to function name)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            name = operation or func.__name__
            
            logger.info(f"Entering {name}")
            try:
                result = func(*args, **kwargs)
                logger.info(f"Exiting {name} successfully")
                return result
            except Exception as e:
                logger.error(f"Exiting {name} with error", exception=str(e))
                raise
        
        return wrapper
    return decorator
