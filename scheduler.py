"""
Scheduler pour sauvegardes programmées KVM
"""
import asyncio
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import uuid

from config import settings
from backup_manager import BackupManager
from models import BackupMode
from logging_config import get_logger

class ScheduledBackup:
    def __init__(self, id: str, name: str, vm_names: List[str], 
                 schedule_type: str, schedule_time: str, 
                 backup_mode: str = "incremental", enabled: bool = True):
        self.id = id
        self.name = name
        self.vm_names = vm_names
        self.schedule_type = schedule_type  # daily, weekly, monthly
        self.schedule_time = schedule_time  # "02:00", "sunday:03:00", "1:04:00"
        self.backup_mode = backup_mode
        self.enabled = enabled
        self.last_run = None
        self.next_run = self._calculate_next_run()
        self.status = "scheduled"  # scheduled, running, completed, failed
        self.created_at = datetime.now()
        
    def _calculate_next_run(self) -> datetime:
        """Calculer la prochaine exécution"""
        now = datetime.now()
        
        if self.schedule_type == "daily":
            # Format: "02:00"
            hour, minute = map(int, self.schedule_time.split(':'))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
                
        elif self.schedule_type == "weekly":
            # Format: "sunday:03:00"
            parts = self.schedule_time.split(':')
            day_name = parts[0]
            hour = int(parts[1])
            minute = int(parts[2])
            
            days = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                   'friday': 4, 'saturday': 5, 'sunday': 6}
            target_day = days[day_name.lower()]
            
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            days_ahead = target_day - now.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            next_run += timedelta(days=days_ahead)
            
        elif self.schedule_type == "monthly":
            # Format: "1:04:00" (jour:heure:minute)
            day, hour, minute = map(int, self.schedule_time.split(':'))
            next_run = now.replace(day=day, hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                # Next month
                if now.month == 12:
                    next_run = next_run.replace(year=now.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=now.month + 1)
        
        return next_run
    
    def update_next_run(self):
        """Mettre à jour la prochaine exécution après une sauvegarde"""
        self.last_run = datetime.now()
        self.next_run = self._calculate_next_run()
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'vm_names': self.vm_names,
            'schedule_type': self.schedule_type,
            'schedule_time': self.schedule_time,
            'backup_mode': self.backup_mode,
            'enabled': self.enabled,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data):
        scheduled = cls(
            id=data['id'],
            name=data['name'],
            vm_names=data['vm_names'],
            schedule_type=data['schedule_type'],
            schedule_time=data['schedule_time'],
            backup_mode=data['backup_mode'],
            enabled=data['enabled']
        )
        if data.get('last_run'):
            scheduled.last_run = datetime.fromisoformat(data['last_run'])
        if data.get('next_run'):
            scheduled.next_run = datetime.fromisoformat(data['next_run'])
        scheduled.status = data.get('status', 'scheduled')
        scheduled.created_at = datetime.fromisoformat(data['created_at'])
        return scheduled

class BackupScheduler:
    def __init__(self):
        self.scheduled_backups: Dict[str, ScheduledBackup] = {}
        self.running = False
        self.logger = get_logger("kvm_backup.scheduler")
        self.storage_file = Path(__file__).parent / "scheduled_backups.json"
        self.backup_manager = BackupManager(settings)
        self.load_scheduled_backups()
        
    def load_scheduled_backups(self):
        """Charger les sauvegardes programmées depuis le fichier"""
        try:
            if self.storage_file.exists():
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        scheduled = ScheduledBackup.from_dict(item)
                        self.scheduled_backups[scheduled.id] = scheduled
                self.logger.info(f"Loaded {len(self.scheduled_backups)} scheduled backups")
        except Exception as e:
            self.logger.error(f"Failed to load scheduled backups: {e}")
    
    def save_scheduled_backups(self):
        """Sauvegarder les sauvegardes programmées dans le fichier"""
        try:
            data = [backup.to_dict() for backup in self.scheduled_backups.values()]
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Saved {len(self.scheduled_backups)} scheduled backups")
        except Exception as e:
            self.logger.error(f"Failed to save scheduled backups: {e}")
    
    def add_scheduled_backup(self, name: str, vm_names: List[str], 
                           schedule_type: str, schedule_time: str,
                           backup_mode: str = "incremental") -> str:
        """Ajouter une nouvelle sauvegarde programmée"""
        backup_id = str(uuid.uuid4())
        scheduled = ScheduledBackup(
            id=backup_id,
            name=name,
            vm_names=vm_names,
            schedule_type=schedule_type,
            schedule_time=schedule_time,
            backup_mode=backup_mode
        )
        
        self.scheduled_backups[backup_id] = scheduled
        self.save_scheduled_backups()
        
        self.logger.info(f"Added scheduled backup: {name} ({backup_id})")
        return backup_id
    
    def remove_scheduled_backup(self, backup_id: str) -> bool:
        """Supprimer une sauvegarde programmée"""
        if backup_id in self.scheduled_backups:
            backup_name = self.scheduled_backups[backup_id].name
            del self.scheduled_backups[backup_id]
            self.save_scheduled_backups()
            self.logger.info(f"Removed scheduled backup: {backup_name} ({backup_id})")
            return True
        return False
    
    def update_scheduled_backup(self, backup_id: str, **kwargs) -> bool:
        """Mettre à jour une sauvegarde programmée"""
        if backup_id not in self.scheduled_backups:
            return False
            
        scheduled = self.scheduled_backups[backup_id]
        for key, value in kwargs.items():
            if hasattr(scheduled, key):
                setattr(scheduled, key, value)
        
        # Recalculer la prochaine exécution si le timing a changé
        if 'schedule_type' in kwargs or 'schedule_time' in kwargs:
            scheduled.next_run = scheduled._calculate_next_run()
        
        self.save_scheduled_backups()
        self.logger.info(f"Updated scheduled backup: {scheduled.name} ({backup_id})")
        return True
    
    def get_scheduled_backups(self) -> List[Dict]:
        """Obtenir toutes les sauvegardes programmées"""
        return [backup.to_dict() for backup in self.scheduled_backups.values()]
    
    def get_due_backups(self) -> List[ScheduledBackup]:
        """Obtenir les sauvegardes qui doivent être exécutées"""
        now = datetime.now()
        due_backups = []
        
        for backup in self.scheduled_backups.values():
            if (backup.enabled and 
                backup.status != "running" and 
                backup.next_run and 
                backup.next_run <= now):
                due_backups.append(backup)
        
        return due_backups
    
    async def execute_scheduled_backup(self, scheduled_backup: ScheduledBackup):
        """Exécuter une sauvegarde programmée"""
        try:
            scheduled_backup.status = "running"
            self.logger.info(f"Starting scheduled backup: {scheduled_backup.name}")
            
            # Créer le job de sauvegarde avec les bonnes options
            backup_job = self.backup_manager.create_backup_job(
                name=f"scheduled_{scheduled_backup.name}_{int(time.time())}",
                vm_names=scheduled_backup.vm_names,
                mode=BackupMode(scheduled_backup.backup_mode),
                use_snapshots=True,  # Utiliser des snapshots pour éviter l'arrêt des VMs
                compress=True  # Compression pour réduire la taille des transferts
            )
            
            # Exécuter la sauvegarde
            result = await self.backup_manager.execute_backup(backup_job)
            
            if result.status.value == "completed":
                scheduled_backup.status = "completed"
                self.logger.info(f"Scheduled backup completed: {scheduled_backup.name} - " +
                               f"Files: {sum(len(vm_result.get('files_backed_up', [])) for vm_result in result.vm_results.values())} - " +
                               f"Size: {result.total_size_bytes / (1024*1024):.1f} MB")
            else:
                scheduled_backup.status = "failed"
                self.logger.error(f"Scheduled backup failed: {scheduled_backup.name} - {result.error_message}")
            
            # Mettre à jour la prochaine exécution
            scheduled_backup.update_next_run()
            scheduled_backup.status = "scheduled"  # Reprogrammer
            
        except Exception as e:
            scheduled_backup.status = "failed"
            self.logger.error(f"Error executing scheduled backup {scheduled_backup.name}: {e}")
            # Reprogrammer même en cas d'erreur
            scheduled_backup.update_next_run()
            scheduled_backup.status = "scheduled"
        
        finally:
            self.save_scheduled_backups()
    
    def start_scheduler(self):
        """Démarrer le scheduler en arrière-plan"""
        self.running = True
        
        def scheduler_loop():
            self.logger.info("Backup scheduler started")
            
            while self.running:
                try:
                    # Vérifier les sauvegardes dues
                    due_backups = self.get_due_backups()
                    
                    for backup in due_backups:
                        # Lancer en arrière-plan avec une nouvelle event loop
                        def run_scheduled_backup(scheduled_backup):
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(self.execute_scheduled_backup(scheduled_backup))
                                loop.close()
                            except Exception as e:
                                self.logger.error(f"Error running scheduled backup: {e}")
                        
                        backup_thread = threading.Thread(
                            target=run_scheduled_backup, 
                            args=(backup,), 
                            daemon=True
                        )
                        backup_thread.start()
                    
                    # Vérifier toutes les minutes
                    time.sleep(60)
                    
                except Exception as e:
                    self.logger.error(f"Scheduler error: {e}")
                    time.sleep(60)
            
            self.logger.info("Backup scheduler stopped")
        
        # Démarrer en thread daemon
        thread = threading.Thread(target=scheduler_loop, daemon=True)
        thread.start()
        self.logger.info("Backup scheduler thread started")
    
    def stop_scheduler(self):
        """Arrêter le scheduler"""
        self.running = False
        self.logger.info("Backup scheduler stopping...")

# Instance globale du scheduler
scheduler = BackupScheduler()
