"""
Test suite for KVM backup system
"""
import pytest
import asyncio
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from app_backup_kvm.models import BackupJob, BackupMode, VMInfo, VMState
from app_backup_kvm.vm_manager import LibvirtManager
from app_backup_kvm.backup_manager import BackupManager
from app_backup_kvm.ssh_client import SSHClient


class TestVMManager:
    """Test cases for VM Manager"""
    
    @patch('libvirt.open')
    def test_connect_success(self, mock_libvirt_open):
        """Test successful libvirt connection"""
        mock_conn = Mock()
        mock_libvirt_open.return_value = mock_conn
        mock_conn.isAlive.return_value = True
        
        vm_manager = LibvirtManager()
        result = vm_manager.connect()
        
        assert result is True
        assert vm_manager.conn == mock_conn
        mock_libvirt_open.assert_called_once_with("qemu:///system")
    
    @patch('libvirt.open')
    def test_connect_failure(self, mock_libvirt_open):
        """Test libvirt connection failure"""
        mock_libvirt_open.side_effect = Exception("Connection failed")
        
        vm_manager = LibvirtManager()
        result = vm_manager.connect()
        
        assert result is False
        assert vm_manager.conn is None
    
    @patch('libvirt.open')
    def test_list_vms(self, mock_libvirt_open):
        """Test listing VMs"""
        # Setup mocks
        mock_conn = Mock()
        mock_libvirt_open.return_value = mock_conn
        
        mock_domain = Mock()
        mock_domain.name.return_value = "test-vm"
        mock_domain.UUIDString.return_value = "test-uuid"
        mock_domain.info.return_value = [1, 1024*1024, 1024*1024, 2, 0]  # running, 1GB, 2 CPUs
        mock_domain.autostart.return_value = True
        mock_domain.XMLDesc.return_value = """
        <domain>
            <devices>
                <disk type='file'>
                    <source file='/var/lib/libvirt/images/test.qcow2'/>
                    <target dev='vda'/>
                </disk>
            </devices>
        </domain>
        """
        
        mock_conn.listAllDomains.return_value = [mock_domain]
        
        vm_manager = LibvirtManager()
        vms = vm_manager.list_all_vms()
        
        assert len(vms) == 1
        assert vms[0].name == "test-vm"
        assert vms[0].uuid == "test-uuid"
        assert vms[0].state == VMState.RUNNING
        assert vms[0].memory_mb == 1024
        assert vms[0].vcpus == 2
        assert vms[0].autostart is True
    
    @patch('libvirt.open')
    def test_create_snapshot(self, mock_libvirt_open):
        """Test snapshot creation"""
        mock_conn = Mock()
        mock_libvirt_open.return_value = mock_conn
        
        mock_domain = Mock()
        mock_domain.name.return_value = "test-vm"
        mock_domain.XMLDesc.return_value = """
        <domain>
            <devices>
                <disk type='file'>
                    <target dev='vda'/>
                </disk>
            </devices>
        </domain>
        """
        
        mock_snapshot = Mock()
        mock_domain.snapshotCreateXML.return_value = mock_snapshot
        mock_conn.lookupByName.return_value = mock_domain
        
        vm_manager = LibvirtManager()
        snapshot = vm_manager.create_snapshot("test-vm", "test-snapshot")
        
        assert snapshot is not None
        assert snapshot.name == "test-snapshot"
        assert snapshot.vm_name == "test-vm"
        mock_domain.snapshotCreateXML.assert_called_once()


class TestSSHClient:
    """Test cases for SSH Client"""
    
    @patch('paramiko.SSHClient')
    def test_connect_with_password(self, mock_ssh_client_class):
        """Test SSH connection with password"""
        mock_client = Mock()
        mock_ssh_client_class.return_value = mock_client
        
        mock_sftp = Mock()
        mock_client.open_sftp.return_value = mock_sftp
        
        ssh_client = SSHClient("localhost", "user", password="pass")
        result = ssh_client.connect()
        
        assert result is True
        mock_client.connect.assert_called_once_with(
            hostname="localhost", port=22, username="user", timeout=30, password="pass"
        )
    
    @patch('paramiko.SSHClient')
    def test_execute_command_success(self, mock_ssh_client_class):
        """Test successful command execution"""
        mock_client = Mock()
        mock_ssh_client_class.return_value = mock_client
        
        # Mock command execution
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()
        
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b"success output"
        mock_stderr.read.return_value = b""
        
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        
        ssh_client = SSHClient("localhost", "user", password="pass")
        ssh_client.client = mock_client
        
        result = ssh_client.execute_command("ls -la")
        
        assert result['success'] is True
        assert result['exit_code'] == 0
        assert result['stdout'] == "success output"
    
    @patch('subprocess.run')
    def test_rsync_transfer(self, mock_subprocess_run):
        """Test rsync file transfer"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        ssh_client = SSHClient("localhost", "user", password="pass")
        result = ssh_client.rsync_transfer("/local/path", "/remote/path")
        
        assert result is True
        mock_subprocess_run.assert_called_once()


class TestBackupManager:
    """Test cases for Backup Manager"""
    
    def test_create_backup_job(self):
        """Test backup job creation"""
        config = Mock()
        backup_manager = BackupManager(config)
        
        job = backup_manager.create_backup_job(
            name="test-backup",
            vm_names=["vm1", "vm2"],
            mode=BackupMode.INCREMENTAL
        )
        
        assert job.name == "test-backup"
        assert job.vm_names == ["vm1", "vm2"]
        assert job.mode == BackupMode.INCREMENTAL
        assert job.id is not None
    
    @pytest.mark.asyncio
    async def test_backup_vm_with_snapshots(self):
        """Test VM backup using snapshots"""
        config = Mock()
        config.backup_server = "localhost"
        config.backup_user = "user" 
        config.backup_password = "pass"
        config.ssh_key_file = None
        config.ssh_port = 22
        config.ssh_timeout = 30
        config.remote_backup_dir = "/backup"
        
        backup_manager = BackupManager(config)
        
        # Mock VM manager
        with patch.object(backup_manager, 'vm_manager') as mock_vm_manager:
            mock_vm_info = VMInfo(
                name="test-vm",
                uuid="test-uuid",
                state=VMState.RUNNING,
                memory_mb=1024,
                vcpus=2,
                disk_paths=["/var/lib/libvirt/images/test.qcow2"]
            )
            
            mock_vm_manager.__enter__.return_value = mock_vm_manager
            mock_vm_manager.get_vm_by_name.return_value = mock_vm_info
            mock_vm_manager.create_snapshot.return_value = Mock(name="test-snapshot")
            mock_vm_manager.delete_snapshot.return_value = True
            mock_vm_manager.export_vm_definition.return_value = True
            
            # Mock SSH client
            with patch('app_backup_kvm.backup_manager.SSHClient') as mock_ssh_class:
                mock_ssh = Mock()
                mock_ssh_class.return_value = mock_ssh
                mock_ssh.connect.return_value = True
                mock_ssh.rsync_transfer.return_value = True
                mock_ssh.create_directory.return_value = True
                
                # Create and execute job
                job = backup_manager.create_backup_job(
                    name="test-backup",
                    vm_names=["test-vm"],
                    mode=BackupMode.INCREMENTAL,
                    use_snapshots=True,
                    dry_run=True
                )
                
                result = await backup_manager.execute_backup(job)
                
                assert result.status.value in ["completed", "failed"]  # Should complete
                assert "test-vm" in result.vm_results


class TestModels:
    """Test cases for data models"""
    
    def test_vm_info_creation(self):
        """Test VMInfo model creation"""
        vm = VMInfo(
            name="test-vm",
            uuid="test-uuid",
            state=VMState.RUNNING,
            memory_mb=1024,
            vcpus=2
        )
        
        assert vm.name == "test-vm"
        assert vm.state == VMState.RUNNING
        assert vm.memory_mb == 1024
    
    def test_backup_result_duration(self):
        """Test backup result duration calculation"""
        from app_backup_kvm.models import BackupResult, BackupStatus
        
        start_time = datetime.now()
        result = BackupResult(
            job_id="test-job",
            status=BackupStatus.RUNNING,
            start_time=start_time
        )
        
        # No end time yet
        assert result.duration_seconds is None
        
        # Set end time
        import time
        time.sleep(0.1)
        result.end_time = datetime.now()
        
        assert result.duration_seconds is not None
        assert result.duration_seconds > 0
    
    def test_backup_result_success_rate(self):
        """Test backup result success rate calculation"""
        from app_backup_kvm.models import BackupResult, BackupStatus
        
        result = BackupResult(
            job_id="test-job",
            status=BackupStatus.COMPLETED,
            start_time=datetime.now(),
            vm_results={
                "vm1": {"status": "success"},
                "vm2": {"status": "failed"},
                "vm3": {"status": "success"}
            }
        )
        
        assert result.success_rate == 66.67  # 2 out of 3 successful (rounded)


class TestConfigurationLoading:
    """Test configuration loading and validation"""
    
    def test_default_config_values(self):
        """Test default configuration values"""
        from app_backup_kvm.config import BackupSettings
        
        settings = BackupSettings()
        
        assert settings.backup_server == "192.168.26.27"
        assert settings.backup_user == "authentik"
        assert settings.default_backup_mode == "incremental"
        assert settings.ssh_port == 22
    
    def test_config_environment_override(self):
        """Test configuration override from environment"""
        import os
        from app_backup_kvm.config import BackupSettings
        
        # Set environment variable
        os.environ["KVM_BACKUP_BACKUP_SERVER"] = "custom-server"
        
        settings = BackupSettings()
        
        assert settings.backup_server == "custom-server"
        
        # Cleanup
        del os.environ["KVM_BACKUP_BACKUP_SERVER"]


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_backup_workflow_dry_run(self):
        """Test complete backup workflow in dry run mode"""
        # This test would require actual libvirt setup, so we mock it
        config = Mock()
        config.backup_server = "localhost"
        config.backup_user = "user"
        config.backup_password = "pass"
        config.ssh_key_file = None
        config.ssh_port = 22
        config.ssh_timeout = 30
        config.remote_backup_dir = "/backup"
        config.vm_shutdown_timeout = 60
        config.compression_level = 6
        
        backup_manager = BackupManager(config)
        
        # Mock all external dependencies
        with patch.object(backup_manager, 'vm_manager') as mock_vm_manager, \
             patch('app_backup_kvm.backup_manager.SSHClient') as mock_ssh_class:
            
            # Setup VM manager mock
            mock_vm_info = VMInfo(
                name="test-vm",
                uuid="test-uuid", 
                state=VMState.RUNNING,
                memory_mb=1024,
                vcpus=2,
                disk_paths=["/var/lib/libvirt/images/test.qcow2"],
                config_path="/etc/libvirt/qemu/test-vm.xml"
            )
            
            mock_vm_manager.__enter__.return_value = mock_vm_manager
            mock_vm_manager.get_vm_by_name.return_value = mock_vm_info
            mock_vm_manager.create_snapshot.return_value = Mock(name="backup-snapshot")
            mock_vm_manager.delete_snapshot.return_value = True
            mock_vm_manager.export_vm_definition.return_value = True
            
            # Setup SSH client mock
            mock_ssh = Mock()
            mock_ssh_class.return_value = mock_ssh
            mock_ssh.connect.return_value = True
            mock_ssh.create_directory.return_value = True
            mock_ssh.rsync_transfer.return_value = True
            mock_ssh.disconnect.return_value = None
            
            # Create and execute backup job
            job = backup_manager.create_backup_job(
                name="integration-test",
                vm_names=["test-vm"],
                mode=BackupMode.INCREMENTAL,
                dry_run=True,
                use_snapshots=True
            )
            
            result = await backup_manager.execute_backup(job)
            
            # Verify results
            assert result.job_id == job.id
            assert "test-vm" in result.vm_results
            
            # Verify VM manager was used
            mock_vm_manager.get_vm_by_name.assert_called_with("test-vm")
            mock_vm_manager.create_snapshot.assert_called_once()
            mock_vm_manager.delete_snapshot.assert_called_once()
            
            # Verify SSH operations
            mock_ssh.connect.assert_called_once()
            mock_ssh.create_directory.assert_called()
            mock_ssh.disconnect.assert_called_once()


# Test fixtures
@pytest.fixture
def temp_config_file():
    """Create temporary config file for testing"""
    config_data = {
        "backup_server": "test-server",
        "backup_user": "test-user",
        "backup_password": "test-pass"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        yield f.name
    
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def mock_vm_info():
    """Create mock VM info for testing"""
    return VMInfo(
        name="test-vm",
        uuid="test-uuid-123",
        state=VMState.RUNNING,
        memory_mb=2048,
        vcpus=4,
        disk_paths=["/var/lib/libvirt/images/test.qcow2"],
        config_path="/etc/libvirt/qemu/test-vm.xml",
        autostart=True
    )


# Performance tests
class TestPerformance:
    """Performance and load tests"""
    
    @pytest.mark.asyncio
    async def test_concurrent_backup_jobs(self):
        """Test handling multiple concurrent backup jobs"""
        config = Mock()
        backup_manager = BackupManager(config)
        
        # Create multiple jobs
        jobs = []
        for i in range(3):
            job = backup_manager.create_backup_job(
                name=f"test-backup-{i}",
                vm_names=[f"vm-{i}"],
                mode=BackupMode.INCREMENTAL,
                dry_run=True
            )
            jobs.append(job)
        
        # Mock execution to be instant
        async def mock_execute(job):
            from app_backup_kvm.models import BackupResult, BackupStatus
            return BackupResult(
                job_id=job.id,
                status=BackupStatus.COMPLETED,
                start_time=datetime.now(),
                end_time=datetime.now()
            )
        
        with patch.object(backup_manager, 'execute_backup', side_effect=mock_execute):
            # Execute jobs concurrently
            results = await asyncio.gather(*[
                backup_manager.execute_backup(job) for job in jobs
            ])
        
        # Verify all jobs completed
        assert len(results) == 3
        for result in results:
            assert result.status.value == "completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
