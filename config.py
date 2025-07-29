"""
Configuration settings for KVM Backup application
"""
from typing import List, Optional
from pathlib import Path
import os
from dataclasses import dataclass

# Load .env file if it exists
def load_env_file():
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env_file()


@dataclass
class BackupSettings:
    """Main configuration for KVM backup system"""
    
    # Basic settings
    backup_server: str = os.getenv("BACKUP_SERVER", "192.168.26.27")
    backup_user: str = os.getenv("BACKUP_USER", "authentik")
    backup_password: str = os.getenv("BACKUP_PASSWORD", "server")
    
    # Directories
    remote_backup_dir: str = os.getenv("REMOTE_BACKUP_DIR", "/home/authentik/backup-kvm")
    local_vm_dir: str = os.getenv("LOCAL_VM_DIR", "/var/lib/libvirt/images")
    config_dir: str = os.getenv("CONFIG_DIR", "/etc/libvirt/qemu")
    log_dir: str = os.getenv("LOG_DIR", "./logs")
    
    # SSH settings
    ssh_port: int = 22
    ssh_timeout: int = 30
    ssh_key_file: Optional[str] = None
    
    # Backup settings
    default_backup_mode: str = "incremental"
    snapshot_timeout: int = 300
    vm_shutdown_timeout: int = 60
    
    # Retention settings
    keep_snapshots: int = 3
    keep_full_backups: int = 7
    keep_incremental_backups: int = 30
    
    # Performance settings
    rsync_parallel_jobs: int = 2
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "json"
    log_file_max_size: int = 10485760  # 10MB
    compression_level: int = 6
    
    # Web API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "your-secret-key-change-this"
    
    # Database
    database_url: str = "sqlite:///kvm_backup.db"
    
    # Monitoring
    enable_metrics: bool = True
    metrics_retention_days: int = 90
    
    def __post_init__(self):
        """Load configuration from environment variables"""
        # Override with environment variables if they exist
        for field_name in self.__dataclass_fields__:
            env_name = f"KVM_BACKUP_{field_name.upper()}"
            env_value = os.getenv(env_name)
            if env_value is not None:
                field_type = self.__dataclass_fields__[field_name].type
                if field_type == int:
                    setattr(self, field_name, int(env_value))
                elif field_type == bool:
                    setattr(self, field_name, env_value.lower() in ('true', '1', 'yes'))
                else:
                    setattr(self, field_name, env_value)


@dataclass
class LoggingSettings:
    """Logging configuration"""
    
    log_level: str = "INFO"
    log_format: str = "json"
    log_file_max_size: str = "10MB"
    log_file_backup_count: int = 5
    
    def __post_init__(self):
        """Load from environment variables"""
        for field_name in self.__dataclass_fields__:
            env_name = f"LOG_{field_name.upper()}"
            env_value = os.getenv(env_name)
            if env_value is not None:
                field_type = self.__dataclass_fields__[field_name].type
                if field_type == int:
                    setattr(self, field_name, int(env_value))
                else:
                    setattr(self, field_name, env_value)


# Global settings instance
settings = BackupSettings()
log_settings = LoggingSettings()
