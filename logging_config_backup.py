"""
Structured logging configuration for KVM backup system
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import json
import sys
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'vm_name'):
            log_data['vm_name'] = record.vm_name
        if hasattr(record, 'backup_id'):
            log_data['backup_id'] = record.backup_id
        if hasattr(record, 'operation'):
            log_data['operation'] = record.operation
        if hasattr(record, 'duration'):
            log_data['duration_seconds'] = record.duration
        if hasattr(record, 'size_bytes'):
            log_data['size_bytes'] = record.size_bytes
            
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_dir: str = "/var/log/kvm-backup",
    log_file_max_size: str = "10MB",
    log_file_backup_count: int = 5
) -> None:
    """Setup structured logging configuration"""
    
    # Create log directory
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
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
        maxBytes=_parse_size(log_file_max_size),
        backupCount=log_file_backup_count,
        encoding='utf-8'
    )
    
    if log_format == "json":
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
    
    root_logger.addHandler(file_handler)
    
    # Setup specific loggers
    setup_component_loggers()


def setup_component_loggers() -> None:
    """Setup loggers for specific components"""
    
    # Reduce external library verbosity
    logging.getLogger('paramiko').setLevel(logging.WARNING)
    
    # Our application loggers
    app_loggers = [
        'kvm_backup.vm_manager',
        'kvm_backup.backup_manager', 
        'kvm_backup.snapshot_manager',
        'kvm_backup.ssh_client',
        'kvm_backup.api'
    ]
    
    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)


def _parse_size(size_str: str) -> int:
    """Parse size string like '10MB' to bytes"""
    size_str = size_str.upper()
    
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        return int(size_str)


def get_logger(name: str):
    """Get a logger instance"""
    return logging.getLogger(name)


# Simple logging context manager
class LogOperation:
    """Context manager for logging operations with timing"""
    
    def __init__(self, logger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
        
    def __enter__(self):
        self.start_time = datetime.now()
        # Create a log record with extra attributes
        record = logging.LogRecord(
            name=self.logger.name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=f"Starting {self.operation}",
            args=(),
            exc_info=None
        )
        for key, value in self.context.items():
            setattr(record, key, value)
        setattr(record, 'operation', self.operation)
        self.logger.handle(record)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            level = logging.INFO
            message = f"Completed {self.operation}"
            status = "success"
        else:
            level = logging.ERROR
            message = f"Failed {self.operation}"
            status = "failed"
        
        record = logging.LogRecord(
            name=self.logger.name,
            level=level,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        
        for key, value in self.context.items():
            setattr(record, key, value)
        setattr(record, 'operation', self.operation)
        setattr(record, 'duration', duration)
        setattr(record, 'status', status)
        if exc_val:
            setattr(record, 'error', str(exc_val))
            
        self.logger.handle(record)


# Utility functions for common logging patterns
def log_vm_operation(logger, vm_name: str, operation: str, **kwargs):
    """Log VM-specific operations"""
    return LogOperation(logger, operation, vm_name=vm_name, **kwargs)


def log_backup_operation(logger, backup_id: str, operation: str, **kwargs):
    """Log backup-specific operations"""
    return LogOperation(logger, operation, backup_id=backup_id, **kwargs)


def log_size_info(logger, message: str, size_bytes: int, **kwargs):
    """Log messages with size information"""
    size_mb = size_bytes / (1024 * 1024)
    size_gb = size_bytes / (1024 * 1024 * 1024)
    
    if size_gb >= 1:
        size_str = f"{size_gb:.2f} GB"
    else:
        size_str = f"{size_mb:.2f} MB"
    
    record = logging.LogRecord(
        name=logger.name,
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    
    setattr(record, 'size_bytes', size_bytes)
    setattr(record, 'size_human', size_str)
    for key, value in kwargs.items():
        setattr(record, key, value)
        
    logger.handle(record)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'vm_name'):
            log_data['vm_name'] = record.vm_name
        if hasattr(record, 'backup_id'):
            log_data['backup_id'] = record.backup_id
        if hasattr(record, 'operation'):
            log_data['operation'] = record.operation
        if hasattr(record, 'duration'):
            log_data['duration_seconds'] = record.duration
        if hasattr(record, 'size_bytes'):
            log_data['size_bytes'] = record.size_bytes
            
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_dir: str = "/var/log/kvm-backup",
    log_file_max_size: str = "10MB",
    log_file_backup_count: int = 5
) -> None:
    """Setup structured logging configuration"""
    
    # Create log directory
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
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
        maxBytes=_parse_size(log_file_max_size),
        backupCount=log_file_backup_count,
        encoding='utf-8'
    )
    
    if log_format == "json":
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
    
    root_logger.addHandler(file_handler)
    
    # Setup specific loggers
    setup_component_loggers()


def setup_component_loggers() -> None:
    """Setup loggers for specific components"""
    
    # Libvirt logger
    libvirt_logger = logging.getLogger('libvirt')
    libvirt_logger.setLevel(logging.WARNING)  # Reduce libvirt verbosity
    
    # Paramiko logger (SSH)
    paramiko_logger = logging.getLogger('paramiko')
    paramiko_logger.setLevel(logging.WARNING)
    
    # Our application loggers
    app_loggers = [
        'kvm_backup.vm_manager',
        'kvm_backup.backup_manager', 
        'kvm_backup.snapshot_manager',
        'kvm_backup.ssh_client',
        'kvm_backup.api'
    ]
    
    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)


def _parse_size(size_str: str) -> int:
    """Parse size string like '10MB' to bytes"""
    size_str = size_str.upper()
    
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        return int(size_str)


def get_logger(name: str):
    """Get a logger instance"""
    return logging.getLogger(name)


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
        self.logger.info(f"Starting {self.operation}", operation=self.operation, **self.context)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.info(
                f"Completed {self.operation}",
                operation=self.operation,
                duration=duration,
                status="success",
                **self.context
            )
        else:
            self.logger.error(
                f"Failed {self.operation}",
                operation=self.operation,
                duration=duration,
                status="failed",
                error=str(exc_val),
                **self.context
            )


# Utility functions for common logging patterns
def log_vm_operation(logger, vm_name: str, operation: str, **kwargs):
    """Log VM-specific operations"""
    return LogOperation(logger, operation, vm_name=vm_name, **kwargs)


def log_backup_operation(logger, backup_id: str, operation: str, **kwargs):
    """Log backup-specific operations"""
    return LogOperation(logger, operation, backup_id=backup_id, **kwargs)


def log_size_info(logger, message: str, size_bytes: int, **kwargs):
    """Log messages with size information"""
    size_mb = size_bytes / (1024 * 1024)
    size_gb = size_bytes / (1024 * 1024 * 1024)
    
    if size_gb >= 1:
        size_str = f"{size_gb:.2f} GB"
    else:
        size_str = f"{size_mb:.2f} MB"
    
    logger.info(
        message,
        size_bytes=size_bytes,
        size_human=size_str,
        **kwargs
    )
