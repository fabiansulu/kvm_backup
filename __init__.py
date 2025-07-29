"""
KVM Backup System - Modern Python replacement for bash backup script

A comprehensive backup solution for KVM/libvirt virtual machines with:
- Snapshot-based backups (no VM downtime)
- Multiple backup modes (full, incremental, sync)
- Web API interface
- Structured logging
- Automated testing
"""

__version__ = "1.0.0"
__author__ = "KVM Backup Team"
__email__ = "support@kvmbackup.com"

from .models import BackupMode, VMState, BackupStatus
from .vm_manager import LibvirtManager
from .backup_manager import BackupManager
from .ssh_client import SSHClient
from .config import settings

__all__ = [
    'BackupMode',
    'VMState', 
    'BackupStatus',
    'LibvirtManager',
    'BackupManager',
    'SSHClient',
    'settings'
]
