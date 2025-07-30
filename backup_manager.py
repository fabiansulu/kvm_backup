"""
Core backup manager with snapshot-based backups
"""
import asyncio
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid
import json

from models import BackupJob, BackupResult, BackupMode, BackupStatus, VMInfo
from vm_manager import LibvirtManager
from ssh_client import SSHClient
from logging_config import get_logger, LogOperation


class BackupManager:
    """Main backup manager with snapshot support"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("kvm_backup.backup_manager")
        self.vm_manager = LibvirtManager()
        
    def create_backup_job(self, name: str, vm_names: List[str], 
                         mode: BackupMode = BackupMode.INCREMENTAL,
                         scheduled_time: Optional[datetime] = None,
                         dry_run: bool = False, **kwargs) -> BackupJob:
        """Create a new backup job"""
        job = BackupJob(
            id=str(uuid.uuid4()),
            name=name,
            mode=mode,
            vm_names=vm_names,
            scheduled_time=scheduled_time,
            dry_run=dry_run,
            **kwargs
        )
        
        self.logger.info("Backup job created", 
                        job_id=job.id, name=name, mode=mode.value, vm_count=len(vm_names))
        return job
    
    async def execute_backup(self, job: BackupJob) -> BackupResult:
        """Execute a backup job"""
        result = BackupResult(
            job_id=job.id,
            status=BackupStatus.RUNNING,
            start_time=datetime.now()
        )
        
        try:
            with LogOperation(self.logger, "execute_backup", 
                            job_id=job.id, mode=job.mode.value, vm_count=len(job.vm_names)):
                
                # Pre-backup script
                if job.pre_backup_script:
                    await self._run_script(job.pre_backup_script, "pre-backup")
                
                # Setup SSH connection
                ssh_client = SSHClient(
                    hostname=self.config.backup_server,
                    username=self.config.backup_user,
                    password=self.config.backup_password,
                    key_filename=self.config.ssh_key_file,
                    port=self.config.ssh_port,
                    timeout=self.config.ssh_timeout
                )
                
                if not ssh_client.connect():
                    raise Exception("Failed to connect to backup server")
                
                try:
                    # Create remote directories
                    remote_dir = self._get_remote_backup_dir(job)
                    ssh_client.create_directory(remote_dir)
                    
                    # Process each VM
                    for vm_name in job.vm_names:
                        vm_result = await self._backup_vm(job, vm_name, ssh_client)
                        result.vm_results[vm_name] = vm_result
                        
                        if vm_result.get('size_bytes', 0) > 0:
                            result.total_size_bytes += vm_result['size_bytes']
                            result.transferred_bytes += vm_result.get('transferred_bytes', 0)
                    
                    # Create backup summary
                    await self._create_backup_summary(job, result, ssh_client)
                    
                    # Post-backup script
                    if job.post_backup_script:
                        await self._run_script(job.post_backup_script, "post-backup")
                    
                    result.status = BackupStatus.COMPLETED
                    
                finally:
                    ssh_client.disconnect()
                    
        except Exception as e:
            self.logger.error("Backup job failed", job_id=job.id, error=str(e))
            result.status = BackupStatus.FAILED
            result.error_message = str(e)
        
        result.end_time = datetime.now()
        
        # Log final result
        if result.status == BackupStatus.COMPLETED:
            self.logger.info("Backup completed successfully",
                           extra={'job_id': job.id, 'total_size_bytes': result.total_size_bytes,
                                 'duration': result.duration_seconds})
        else:
            self.logger.error("Backup failed", job_id=job.id, 
                            error=result.error_message, duration=result.duration_seconds)
        
        return result
    
    async def _backup_vm(self, job: BackupJob, vm_name: str, ssh_client: SSHClient) -> Dict[str, Any]:
        """Backup a single VM"""
        vm_result = {
            'vm_name': vm_name,
            'status': 'pending',
            'snapshots_created': [],
            'files_backed_up': [],
            'size_bytes': 0,
            'transferred_bytes': 0,
            'error': None
        }
        
        try:
            with self.vm_manager:
                vm_info = self.vm_manager.get_vm_by_name(vm_name)
                if not vm_info:
                    raise Exception(f"VM '{vm_name}' not found")
                
                # Strategy based on VM state and job configuration
                if job.use_snapshots:
                    vm_result.update(await self._backup_vm_with_snapshots(
                        job, vm_info, ssh_client))
                else:
                    vm_result.update(await self._backup_vm_traditional(
                        job, vm_info, ssh_client))
                
                vm_result['status'] = 'success'
                
        except Exception as e:
            self.logger.error("VM backup failed", vm_name=vm_name, error=str(e))
            vm_result['status'] = 'failed'
            vm_result['error'] = str(e)
        
        return vm_result
    
    async def _backup_vm_with_snapshots(self, job: BackupJob, vm_info: VMInfo, 
                                       ssh_client: SSHClient) -> Dict[str, Any]:
        """Backup VM using snapshots (no VM downtime)"""
        result = {
            'snapshots_created': [],
            'files_backed_up': [],
            'size_bytes': 0,
            'transferred_bytes': 0,
            'method': 'snapshot'
        }
        
        snapshot_name = f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        try:
            # Create snapshot
            with self.vm_manager:
                snapshot_info = self.vm_manager.create_snapshot(vm_info.name, snapshot_name)
                if not snapshot_info:
                    raise Exception("Failed to create snapshot")
                
                result['snapshots_created'].append(snapshot_name)
                
                # Backup configuration and definition
                await self._backup_vm_config(job, vm_info, ssh_client, result)
                
                # Backup disk files
                await self._backup_vm_disks(job, vm_info, ssh_client, result)
                
                # Clean up snapshot
                if not job.dry_run:
                    self.vm_manager.delete_snapshot(vm_info.name, snapshot_name)
                    result['snapshots_created'].remove(snapshot_name)
        
        except Exception as e:
            # Clean up snapshot on error
            if snapshot_name in result['snapshots_created']:
                try:
                    with self.vm_manager:
                        self.vm_manager.delete_snapshot(vm_info.name, snapshot_name)
                except Exception as cleanup_error:
                    self.logger.warning("Failed to cleanup snapshot", 
                                      vm_name=vm_info.name, snapshot_name=snapshot_name,
                                      error=str(cleanup_error))
            raise e
        
        return result
    
    async def _backup_vm_traditional(self, job: BackupJob, vm_info: VMInfo, 
                                    ssh_client: SSHClient) -> Dict[str, Any]:
        """Traditional backup with VM shutdown"""
        result = {
            'files_backed_up': [],
            'size_bytes': 0,
            'transferred_bytes': 0,
            'method': 'traditional',
            'vm_was_stopped': False
        }
        
        vm_was_running = False
        
        try:
            with self.vm_manager:
                # Check if VM is running
                current_vm_info = self.vm_manager.get_vm_by_name(vm_info.name)
                vm_was_running = current_vm_info and current_vm_info.state.value == 'running'
                
                # Stop VM if running
                if vm_was_running and not job.dry_run:
                    self.logger.info("Stopping VM for backup", vm_name=vm_info.name)
                    if not self.vm_manager.shutdown_vm(vm_info.name, self.config.vm_shutdown_timeout):
                        raise Exception(f"Failed to stop VM {vm_info.name}")
                    result['vm_was_stopped'] = True
                
                # Backup configuration and definition
                await self._backup_vm_config(job, vm_info, ssh_client, result)
                
                # Backup disk files
                await self._backup_vm_disks(job, vm_info, ssh_client, result)
                
                # Restart VM if it was running
                if vm_was_running and not job.dry_run:
                    self.logger.info("Restarting VM after backup", vm_name=vm_info.name)
                    if not self.vm_manager.start_vm(vm_info.name):
                        self.logger.error("Failed to restart VM", vm_name=vm_info.name)
        
        except Exception as e:
            # Try to restart VM on error
            if vm_was_running and result['vm_was_stopped']:
                try:
                    with self.vm_manager:
                        self.vm_manager.start_vm(vm_info.name)
                except Exception as restart_error:
                    self.logger.error("Failed to restart VM after backup error", 
                                    vm_name=vm_info.name, error=str(restart_error))
            raise e
        
        return result
    
    async def _backup_vm_config(self, job: BackupJob, vm_info: VMInfo, 
                               ssh_client: SSHClient, result: Dict[str, Any]) -> None:
        """Backup VM configuration files"""
        remote_dir = self._get_remote_backup_dir(job)
        config_dir = f"{remote_dir}/configs"
        
        if not job.dry_run:
            ssh_client.create_directory(config_dir)
        
        # Export VM definition
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as tmp_file:
            try:
                with self.vm_manager:
                    if self.vm_manager.export_vm_definition(vm_info.name, tmp_file.name):
                        remote_xml_path = f"{config_dir}/{vm_info.name}.xml"
                        
                        if not job.dry_run:
                            ssh_client.rsync_transfer(
                                tmp_file.name, remote_xml_path,
                                options=['-avz'], dry_run=job.dry_run
                            )
                        
                        result['files_backed_up'].append(f"definition:{remote_xml_path}")
                        
                        # Add file size
                        file_size = Path(tmp_file.name).stat().st_size
                        result['size_bytes'] += file_size
            finally:
                Path(tmp_file.name).unlink(missing_ok=True)
        
        # Backup libvirt config file if exists
        if vm_info.config_path and Path(vm_info.config_path).exists():
            remote_config_path = f"{config_dir}/{vm_info.name}_config.xml"
            
            if not job.dry_run:
                # Use sudo to copy protected libvirt files
                success = await self._secure_file_transfer(
                    vm_info.config_path, remote_config_path, ssh_client
                )
                if success:
                    result['files_backed_up'].append(f"config:{remote_config_path}")
                    # Get file size with sudo
                    import subprocess
                    size_result = subprocess.run(['sudo', 'stat', '-c', '%s', vm_info.config_path], 
                                               capture_output=True, text=True)
                    if size_result.returncode == 0:
                        result['size_bytes'] += int(size_result.stdout.strip())
            else:
                result['files_backed_up'].append(f"config:{remote_config_path}")
    
    async def _secure_file_transfer(self, local_path: str, remote_path: str, ssh_client: SSHClient) -> bool:
        """Transfer protected files using sudo to copy to temp location first"""
        import tempfile
        import subprocess
        
        try:
            # Create a temporary file accessible to current user
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # Copy the protected file to temp location with sudo
            copy_result = subprocess.run(['sudo', 'cp', local_path, tmp_path], 
                                       capture_output=True, text=True)
            if copy_result.returncode != 0:
                self.logger.error("Failed to copy protected file", 
                                local_path=local_path, error=copy_result.stderr)
                return False
            
            # Make temp file readable by current user
            subprocess.run(['sudo', 'chown', f"{os.getuid()}:{os.getgid()}", tmp_path])
            
            # Transfer the temp file via SSH
            success = ssh_client.rsync_transfer(tmp_path, remote_path, options=['-avz'])
            
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)
            
            return success
            
        except Exception as e:
            self.logger.error("Secure file transfer failed", 
                            local_path=local_path, remote_path=remote_path, error=str(e))
            return False
    
    async def _backup_vm_disks(self, job: BackupJob, vm_info: VMInfo, 
                              ssh_client: SSHClient, result: Dict[str, Any]) -> None:
        """Backup VM disk files"""
        remote_dir = self._get_remote_backup_dir(job)
        images_dir = f"{remote_dir}/images"
        
        if not job.dry_run:
            ssh_client.create_directory(images_dir)
        
        rsync_options = ['-avz', '--progress']
        
        # Add compression if enabled
        if job.compress:
            rsync_options.append(f'--compress-level={self.config.compression_level}')
        
        # Mode-specific options
        if job.mode == BackupMode.INCREMENTAL:
            rsync_options.extend(['--delete', '--partial', '--inplace'])
            # Use link-dest for space efficiency if previous backup exists
            previous_backup = self._get_previous_backup_dir(job, ssh_client)
            if previous_backup:
                rsync_options.append(f'--link-dest={previous_backup}/images')
        elif job.mode == BackupMode.SYNC:
            rsync_options.extend(['--delete', '--partial'])
        
        # Backup each disk
        for disk_path in vm_info.disk_paths:
            disk_file = Path(disk_path)
            if not disk_file.exists():
                self.logger.warning("Disk file not found", 
                                  vm_name=vm_info.name, disk_path=disk_path)
                continue
            
            remote_disk_path = f"{images_dir}/{disk_file.name}"
            
            # Calculate original size using sudo for protected files
            import subprocess
            size_result = subprocess.run(['sudo', 'stat', '-c', '%s', str(disk_file)], 
                                       capture_output=True, text=True)
            if size_result.returncode == 0:
                disk_size = int(size_result.stdout.strip())
                result['size_bytes'] += disk_size
            else:
                self.logger.warning("Could not get disk size", disk_path=disk_path)
                continue
            
            # Transfer disk using secure method for protected files
            if not job.dry_run:
                transfer_success = await self._secure_file_transfer(
                    str(disk_file), remote_disk_path, ssh_client
                )
            else:
                transfer_success = True
            
            if transfer_success:
                result['files_backed_up'].append(f"disk:{remote_disk_path}")
                # For incremental, only partial data might be transferred
                if job.mode == BackupMode.INCREMENTAL:
                    # Estimate transferred size (simplified)
                    result['transferred_bytes'] += disk_size // 10  # Rough estimate
                else:
                    result['transferred_bytes'] += disk_size
            else:
                raise Exception(f"Failed to backup disk {disk_path}")
    
    def _get_remote_backup_dir(self, job: BackupJob) -> str:
        """Get remote backup directory based on job mode"""
        base_dir = self.config.remote_backup_dir
        
        if job.mode == BackupMode.FULL:
            return f"{base_dir}/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        elif job.mode == BackupMode.INCREMENTAL:
            return f"{base_dir}/latest"
        elif job.mode == BackupMode.SYNC:
            return f"{base_dir}/sync"
        else:
            return f"{base_dir}/snapshot-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    
    def _get_previous_backup_dir(self, job: BackupJob, ssh_client: SSHClient) -> Optional[str]:
        """Get previous backup directory for incremental backups"""
        if job.mode != BackupMode.INCREMENTAL:
            return None
        
        base_dir = self.config.remote_backup_dir
        previous_dir = f"{base_dir}/previous"
        
        if ssh_client.directory_exists(previous_dir):
            return previous_dir
        
        return None
    
    async def _create_backup_summary(self, job: BackupJob, result: BackupResult, 
                                   ssh_client: SSHClient) -> None:
        """Create backup summary file"""
        summary = {
            'backup_info': {
                'job_id': job.id,
                'job_name': job.name,
                'mode': job.mode.value,
                'start_time': result.start_time.isoformat(),
                'end_time': result.end_time.isoformat() if result.end_time else None,
                'duration_seconds': result.duration_seconds,
                'status': result.status.value,
                'dry_run': job.dry_run
            },
            'vm_results': result.vm_results,
            'statistics': {
                'total_vms': len(job.vm_names),
                'successful_vms': len([r for r in result.vm_results.values() if r.get('status') == 'success']),
                'total_size_bytes': result.total_size_bytes,
                'transferred_bytes': result.transferred_bytes,
                'compression_ratio': (1 - result.transferred_bytes / result.total_size_bytes) if result.total_size_bytes > 0 else 0
            },
            'system_info': {
                'backup_server': self.config.backup_server,
                'libvirt_uri': 'qemu:///system',
                'python_version': str(sys.version_info[:3]) if 'sys' in globals() else 'unknown'
            }
        }
        
        # Write summary to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            try:
                json.dump(summary, tmp_file, indent=2)
                tmp_file.flush()
                
                remote_dir = self._get_remote_backup_dir(job)
                remote_summary_path = f"{remote_dir}/backup_summary.json"
                
                if not job.dry_run:
                    ssh_client.rsync_transfer(
                        tmp_file.name, remote_summary_path,
                        options=['-avz'], dry_run=job.dry_run
                    )
                
                self.logger.info("Backup summary created", 
                               job_id=job.id, summary_path=remote_summary_path)
            finally:
                Path(tmp_file.name).unlink(missing_ok=True)
    
    async def _run_script(self, script_path: str, script_type: str) -> None:
        """Run pre/post backup script"""
        try:
            import subprocess
            result = subprocess.run([script_path], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.logger.info(f"{script_type} script completed successfully", 
                               script_path=script_path)
            else:
                self.logger.error(f"{script_type} script failed", 
                                script_path=script_path, 
                                exit_code=result.returncode,
                                stderr=result.stderr)
                
        except Exception as e:
            self.logger.error(f"Error running {script_type} script", 
                            script_path=script_path, error=str(e))
