"""
Core models for KVM backup system
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pathlib import Path


class BackupMode(Enum):
    """Backup mode enumeration"""
    FULL = "full"
    INCREMENTAL = "incremental"
    SYNC = "sync"
    SNAPSHOT = "snapshot"


class VMState(Enum):
    """Virtual Machine state enumeration"""
    RUNNING = "running"
    PAUSED = "paused"
    SHUTDOWN = "shutdown"
    CRASHED = "crashed"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class BackupStatus(Enum):
    """Backup operation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class VMInfo:
    """Virtual Machine information"""
    name: str
    uuid: str
    state: VMState
    memory_mb: int
    vcpus: int
    disk_paths: List[str] = field(default_factory=list)
    config_path: Optional[str] = None
    autostart: bool = False
    
    @classmethod
    def from_libvirt_domain(cls, domain) -> 'VMInfo':
        """Create VMInfo from libvirt domain object"""
        info = domain.info()
        state_map = {
            0: VMState.UNKNOWN,
            1: VMState.RUNNING,
            2: VMState.UNKNOWN,
            3: VMState.PAUSED,
            4: VMState.SHUTDOWN,
            5: VMState.SHUTDOWN,
            6: VMState.CRASHED,
            7: VMState.SUSPENDED
        }
        
        return cls(
            name=domain.name(),
            uuid=domain.UUIDString(),
            state=state_map.get(info[0], VMState.UNKNOWN),
            memory_mb=info[1] // 1024,
            vcpus=info[3]
        )


@dataclass
class SnapshotInfo:
    """Snapshot information"""
    name: str
    vm_name: str
    creation_time: datetime
    description: str = ""
    size_bytes: int = 0
    disk_snapshots: List[str] = field(default_factory=list)


@dataclass
class BackupJob:
    """Backup job configuration"""
    id: str
    name: str
    mode: BackupMode
    vm_names: List[str]
    scheduled_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    dry_run: bool = False
    use_snapshots: bool = True
    compress: bool = True
    parallel_jobs: int = 1
    
    # Advanced options
    exclude_patterns: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    pre_backup_script: Optional[str] = None
    post_backup_script: Optional[str] = None


@dataclass
class BackupResult:
    """Backup operation result"""
    job_id: str
    status: BackupStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    vm_results: Dict[str, Any] = field(default_factory=dict)
    total_size_bytes: int = 0
    transferred_bytes: int = 0
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate backup duration in seconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if not self.vm_results:
            return 0.0
        
        successful = sum(1 for result in self.vm_results.values() 
                        if result.get('status') == 'success')
        return (successful / len(self.vm_results)) * 100


@dataclass
class BackupStatistics:
    """Backup system statistics"""
    total_backups: int = 0
    successful_backups: int = 0
    failed_backups: int = 0
    total_data_backed_up_gb: float = 0.0
    average_backup_duration_minutes: float = 0.0
    last_backup_time: Optional[datetime] = None
    disk_usage_gb: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate overall success rate"""
        if self.total_backups == 0:
            return 0.0
        return (self.successful_backups / self.total_backups) * 100
