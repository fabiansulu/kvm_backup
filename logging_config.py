"""
Simple logging configuration for KVM Backup System
"""
import logging
import logging.handlers
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in {'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'message'}:
                log_entry[key] = value
        
        return json.dumps(log_entry)


def setup_logging(log_level: str = "INFO", 
                 log_format: str = "json",
                 log_dir: str = "./logs",
                 log_file_max_size: int = 10485760):
    """Setup simple logging configuration"""
    
    # Create log directory
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    if log_format == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = Path(log_dir) / "kvm-backup.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=log_file_max_size,
        backupCount=5,
        encoding='utf-8'
    )
    
    if log_format == "json":
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
    
    root_logger.addHandler(file_handler)
    
    # Set levels for specific loggers
    logging.getLogger('paramiko').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def get_logger(name: str):
    """Get a logger instance with enhanced functionality"""
    
    class EnhancedLogger:
        def __init__(self, logger):
            self._logger = logger
        
        def _log_with_kwargs(self, level, msg, *args, **kwargs):
            """Log with keyword arguments support"""
            extra = kwargs.pop('extra', {})
            # Move all remaining kwargs to extra
            for key, value in kwargs.items():
                extra[key] = value
            
            if extra:
                self._logger.log(level, msg, *args, extra=extra)
            else:
                self._logger.log(level, msg, *args)
        
        def info(self, msg, *args, **kwargs):
            self._log_with_kwargs(logging.INFO, msg, *args, **kwargs)
        
        def error(self, msg, *args, **kwargs):
            self._log_with_kwargs(logging.ERROR, msg, *args, **kwargs)
        
        def warning(self, msg, *args, **kwargs):
            self._log_with_kwargs(logging.WARNING, msg, *args, **kwargs)
        
        def debug(self, msg, *args, **kwargs):
            self._log_with_kwargs(logging.DEBUG, msg, *args, **kwargs)
    
    return EnhancedLogger(logging.getLogger(name))


# Context manager for operation logging
class LogOperation:
    """Context manager for logging operations with timing"""
    
    def __init__(self, logger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"Starting {self.operation}", extra={
            'operation': self.operation,
            'phase': 'start',
            **self.context
        })
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = datetime.now() - self.start_time
        
        if exc_type is None:
            self.logger.info(f"Completed {self.operation}", extra={
                'operation': self.operation,
                'phase': 'complete',
                'duration_seconds': duration.total_seconds(),
                **self.context
            })
        else:
            self.logger.error(f"Failed {self.operation}", extra={
                'operation': self.operation,
                'phase': 'failed',
                'duration_seconds': duration.total_seconds(),
                'error': str(exc_val),
                **self.context
            })
