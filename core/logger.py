"""
Production-Grade Structured JSON Logger for Sentinel-X.

Provides enterprise-level logging with:
- JSON-formatted logs for easy parsing
- Log rotation (daily + size-based)
- Context injection (trade_id, symbol, etc)
- Dual output (console + file)
- Thread-safe operation
"""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Dict, Any, Optional


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs as JSON.
    
    Includes timestamp, level, module, message, and extra context.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        
        # Base log structure
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra context (from logger.info(..., extra={...}))
        if hasattr(record, 'context'):
            log_data["context"] = record.context
        
        return json.dumps(log_data, ensure_ascii=False)


class SentinelXLogger:
    """
    Central logging manager for Sentinel-X.
    
    Features:
    - JSON-formatted logs
    - File rotation (daily + 10MB size limit)
    - Console output (development)
    - Context injection
    """
    
    def __init__(
        self,
        name: str = "sentinelx",
        log_dir: str = "logs",
        log_level: str = "INFO",
        console_output: bool = True,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
    ):
        """
        Initialize logger.
        
        Args:
            name: Logger name
            log_dir: Directory for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console_output: Whether to output to console
            max_bytes: Max file size before rotation (default 10MB)
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.console_output = console_output
        self.max_bytes = max_bytes
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.log_level)
        self.logger.propagate = False  # Don't propagate to root logger
        
        # Setup handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup file and console handlers."""
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON Formatter
        json_formatter = JSONFormatter()
        
        # File Handler: Daily rotation + size limit
        log_file = self.log_dir / f"{self.name}.log"
        
        # Use RotatingFileHandler for size-based rotation
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=self.max_bytes,
            backupCount=10,  # Keep 10 old files
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(json_formatter)
        self.logger.addHandler(file_handler)
        
        # Console Handler (optional, for development)
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            
            # Use simple format for console (not JSON)
            console_format = logging.Formatter(
                '[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_format)
            self.logger.addHandler(console_handler)
    
    def get_logger(self, module_name: Optional[str] = None) -> logging.Logger:
        """
        Get logger for specific module.
        
        Args:
            module_name: Optional module name for namespacing
        
        Returns:
            Logger instance
        """
        if module_name:
            return logging.getLogger(f"{self.name}.{module_name}")
        return self.logger


# Global logger instance
_logger_instance: Optional[SentinelXLogger] = None


def initialize_logger(
    log_dir: str = "logs",
    log_level: str = "INFO",
    console_output: bool = True
) -> SentinelXLogger:
    """
    Initialize global logger instance.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level
        console_output: Enable console output
    
    Returns:
        SentinelXLogger instance
    """
    global _logger_instance
    
    # Try to use AppData path if available
    try:
        from .appdata import get_appdata_path
        log_dir = get_appdata_path("logs")
    except Exception:
        pass  # Use provided log_dir
    
    _logger_instance = SentinelXLogger(
        name="sentinelx",
        log_dir=log_dir,
        log_level=log_level,
        console_output=console_output
    )
    
    return _logger_instance


def get_logger(module_name: Optional[str] = None) -> logging.Logger:
    """
    Get logger instance for a module.
    
    Usage:
        from core.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Message", extra={"context": {"key": "value"}})
    
    Args:
        module_name: Module name (use __name__)
    
    Returns:
        Logger instance
    """
    global _logger_instance
    
    # Auto-initialize if not done
    if _logger_instance is None:
        initialize_logger()
    
    return _logger_instance.get_logger(module_name)


class LogContext:
    """
    Context manager for adding context to all logs within a scope.
    
    Usage:
        with LogContext({"trade_id": "BTC_001", "symbol": "BTCUSDT"}):
            logger.info("Trade executed")
            # Log will include trade_id and symbol
    """
    
    def __init__(self, context: Dict[str, Any]):
        """
        Args:
            context: Context dictionary to inject
        """
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        """Enter context - install custom log record factory."""
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            # Add context to record
            if hasattr(record, 'context'):
                record.context.update(self.context)
            else:
                record.context = self.context.copy()
            return record
        
        self.old_factory = old_factory
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore original factory."""
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


# Convenience functions for direct logging
def log_trade_decision(
    symbol: str,
    decision: str,
    confidence: float,
    pro_score: int,
    con_score: int,
    reasoning: str
):
    """
    Log trade decision with full context.
    
    Args:
        symbol: Trading symbol
        decision: BUY/SELL/HOLD
        confidence: Confidence score (0-1)
        pro_score: Pro agent score
        con_score: Con agent score
        reasoning: Judge's reasoning
    """
    logger = get_logger("judge")
    logger.info(
        f"Trade decision: {decision}",
        extra={
            "context": {
                "symbol": symbol,
                "decision": decision,
                "confidence": confidence,
                "pro_score": pro_score,
                "con_score": con_score,
                "reasoning": reasoning
            }
        }
    )


def log_api_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration_ms: float,
    error: Optional[str] = None
):
    """
    Log API request with timing.
    
    Args:
        method: HTTP method
        endpoint: API endpoint
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        error: Error message if any
    """
    logger = get_logger("api")
    
    context = {
        "method": method,
        "endpoint": endpoint,
        "status_code": status_code,
        "duration_ms": duration_ms
    }
    
    if error:
        context["error"] = error
        logger.error(f"API request failed: {method} {endpoint}", extra={"context": context})
    else:
        logger.info(f"API request: {method} {endpoint}", extra={"context": context})


def log_database_operation(
    operation: str,
    table: str,
    duration_ms: float,
    rows_affected: int = 0,
    error: Optional[str] = None
):
    """
    Log database operation.
    
    Args:
        operation: Operation type (SELECT, INSERT, UPDATE, DELETE)
        table: Table name
        duration_ms: Query duration in milliseconds
        rows_affected: Number of rows affected
        error: Error message if any
    """
    logger = get_logger("database")
    
    context = {
        "operation": operation,
        "table": table,
        "duration_ms": duration_ms,
        "rows_affected": rows_affected
    }
    
    if error:
        context["error"] = error
        logger.error(f"Database error: {operation} {table}", extra={"context": context})
    else:
        logger.debug(f"DB operation: {operation} {table}", extra={"context": context})
