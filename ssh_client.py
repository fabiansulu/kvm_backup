"""
SSH client for remote backup operations
"""
import paramiko
import os
import stat
from typing import Optional, List, Dict, Any
from pathlib import Path
import time

from logging_config import get_logger, LogOperation


class SSHClient:
    """Enhanced SSH client for backup operations"""
    
    def __init__(self, hostname: str, username: str, password: Optional[str] = None,
                 key_filename: Optional[str] = None, port: int = 22, timeout: int = 30):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.port = port
        self.timeout = timeout
        
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None
        self.logger = get_logger("kvm_backup.ssh_client")
    
    def connect(self) -> bool:
        """Establish SSH connection"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                'hostname': self.hostname,
                'port': self.port,
                'username': self.username,
                'timeout': self.timeout
            }
            
            if self.key_filename:
                connect_kwargs['key_filename'] = self.key_filename
            elif self.password:
                connect_kwargs['password'] = self.password
            else:
                raise ValueError("Either password or key_filename must be provided")
            
            with LogOperation(self.logger, "ssh_connect", hostname=self.hostname, username=self.username):
                self.client.connect(**connect_kwargs)
                self.sftp = self.client.open_sftp()
                
            self.logger.info("SSH connection established", 
                           hostname=self.hostname, username=self.username)
            return True
            
        except Exception as e:
            self.logger.error("SSH connection failed", 
                            hostname=self.hostname, username=self.username, error=str(e))
            return False
    
    def disconnect(self) -> None:
        """Close SSH connection"""
        if self.sftp:
            self.sftp.close()
            self.sftp = None
        
        if self.client:
            self.client.close()
            self.client = None
            
        self.logger.info("SSH connection closed", hostname=self.hostname)
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    def execute_command(self, command: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute command on remote server"""
        if not self.client:
            raise RuntimeError("SSH client not connected")
        
        try:
            with LogOperation(self.logger, "execute_command", command=command):
                stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
                
                exit_code = stdout.channel.recv_exit_status()
                stdout_data = stdout.read().decode('utf-8')
                stderr_data = stderr.read().decode('utf-8')
                
                result = {
                    'exit_code': exit_code,
                    'stdout': stdout_data,
                    'stderr': stderr_data,
                    'success': exit_code == 0
                }
                
                if exit_code == 0:
                    self.logger.info("Command executed successfully", command=command)
                else:
                    self.logger.error("Command failed", command=command, 
                                    exit_code=exit_code, stderr=stderr_data)
                
                return result
                
        except Exception as e:
            self.logger.error("Command execution error", command=command, error=str(e))
            return {
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e),
                'success': False
            }
    
    def create_directory(self, remote_path: str, recursive: bool = True) -> bool:
        """Create directory on remote server"""
        if not self.sftp:
            return False
        
        try:
            if recursive:
                # Create parent directories if needed
                path_parts = Path(remote_path).parts
                current_path = ""
                
                for part in path_parts:
                    if current_path:
                        current_path = f"{current_path}/{part}"
                    else:
                        current_path = part
                    
                    try:
                        self.sftp.stat(current_path)
                    except FileNotFoundError:
                        self.sftp.mkdir(current_path)
            else:
                self.sftp.mkdir(remote_path)
            
            self.logger.info("Directory created", remote_path=remote_path)
            return True
            
        except Exception as e:
            self.logger.error("Failed to create directory", 
                            remote_path=remote_path, error=str(e))
            return False
    
    def directory_exists(self, remote_path: str) -> bool:
        """Check if directory exists on remote server"""
        if not self.sftp:
            return False
        
        try:
            stat_info = self.sftp.stat(remote_path)
            return stat.S_ISDIR(stat_info.st_mode)
        except FileNotFoundError:
            return False
        except Exception as e:
            self.logger.warning("Error checking directory", 
                              remote_path=remote_path, error=str(e))
            return False
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists on remote server"""
        if not self.sftp:
            return False
        
        try:
            stat_info = self.sftp.stat(remote_path)
            return stat.S_ISREG(stat_info.st_mode)
        except FileNotFoundError:
            return False
        except Exception as e:
            self.logger.warning("Error checking file", 
                              remote_path=remote_path, error=str(e))
            return False
    
    def get_file_size(self, remote_path: str) -> Optional[int]:
        """Get file size on remote server"""
        if not self.sftp:
            return None
        
        try:
            stat_info = self.sftp.stat(remote_path)
            return stat_info.st_size
        except Exception as e:
            self.logger.warning("Error getting file size", 
                              remote_path=remote_path, error=str(e))
            return None
    
    def list_directory(self, remote_path: str) -> List[str]:
        """List directory contents on remote server"""
        if not self.sftp:
            return []
        
        try:
            return self.sftp.listdir(remote_path)
        except Exception as e:
            self.logger.error("Failed to list directory", 
                            remote_path=remote_path, error=str(e))
            return []
    
    def rsync_transfer(self, local_path: str, remote_path: str, 
                      options: List[str] = None, dry_run: bool = False) -> bool:
        """Transfer files using rsync over SSH"""
        if options is None:
            options = ['-avz', '--progress']
        
        if dry_run:
            options.append('--dry-run')
        
        # Build rsync command
        rsync_cmd = ['rsync'] + options
        rsync_cmd.extend([
            '-e', f'ssh -p {self.port} -o StrictHostKeyChecking=no',
            local_path,
            f'{self.username}@{self.hostname}:{remote_path}'
        ])
        
        # Use sshpass if password authentication
        if self.password:
            rsync_cmd = ['sshpass', '-p', self.password] + rsync_cmd
        
        command = ' '.join(rsync_cmd)
        
        try:
            with LogOperation(self.logger, "rsync_transfer", 
                            local_path=local_path, remote_path=remote_path, dry_run=dry_run):
                import subprocess
                
                result = subprocess.run(rsync_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.logger.info("Rsync transfer completed", 
                                   local_path=local_path, remote_path=remote_path)
                    return True
                else:
                    self.logger.error("Rsync transfer failed", 
                                    local_path=local_path, remote_path=remote_path,
                                    exit_code=result.returncode, stderr=result.stderr)
                    return False
                    
        except Exception as e:
            self.logger.error("Rsync transfer error", 
                            local_path=local_path, remote_path=remote_path, error=str(e))
            return False
    
    def get_disk_usage(self, remote_path: str) -> Optional[Dict[str, int]]:
        """Get disk usage information for remote path"""
        command = f"df -B1 '{remote_path}'"
        result = self.execute_command(command)
        
        if not result['success']:
            return None
        
        try:
            lines = result['stdout'].strip().split('\n')
            if len(lines) >= 2:
                fields = lines[1].split()
                if len(fields) >= 4:
                    return {
                        'total': int(fields[1]),
                        'used': int(fields[2]),
                        'available': int(fields[3])
                    }
        except (ValueError, IndexError) as e:
            self.logger.warning("Failed to parse disk usage", error=str(e))
        
        return None
    
    def cleanup_old_backups(self, backup_dir: str, keep_count: int, pattern: str = "*") -> int:
        """Clean up old backup files/directories"""
        command = f"""
        cd '{backup_dir}' && 
        ls -1t {pattern} 2>/dev/null | 
        tail -n +{keep_count + 1} | 
        while read file; do 
            echo "Removing: $file"
            rm -rf "$file"
        done
        """
        
        result = self.execute_command(command)
        
        if result['success']:
            # Count removed items
            removed_count = result['stdout'].count('Removing:')
            self.logger.info("Cleaned up old backups", 
                           backup_dir=backup_dir, removed_count=removed_count)
            return removed_count
        else:
            self.logger.error("Failed to cleanup old backups", 
                            backup_dir=backup_dir, error=result['stderr'])
            return 0
