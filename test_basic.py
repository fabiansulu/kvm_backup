#!/usr/bin/env python3
"""
Simple test script to verify the KVM Backup system works
"""
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        from config import settings
        print("✅ Config module imported")
    except Exception as e:
        print(f"❌ Config import failed: {e}")
        return False
    
    try:
        from models import BackupMode, VMState, VMInfo
        print("✅ Models module imported")
    except Exception as e:
        print(f"❌ Models import failed: {e}")
        return False
    
    try:
        from logging_config import setup_logging, get_logger
        print("✅ Logging module imported")
    except Exception as e:
        print(f"❌ Logging import failed: {e}")
        return False
    
    try:
        from ssh_client import SSHClient
        print("✅ SSH client module imported")
    except Exception as e:
        print(f"❌ SSH client import failed: {e}")
        return False
    
    # Try to import libvirt-dependent modules
    try:
        import libvirt
        from vm_manager import LibvirtManager
        print("✅ VM manager module imported")
    except ImportError:
        print("⚠️  Libvirt not available - VM manager skipped")
    except Exception as e:
        print(f"❌ VM manager import failed: {e}")
        return False
    
    try:
        from backup_manager import BackupManager
        print("✅ Backup manager module imported")
    except Exception as e:
        print(f"❌ Backup manager import failed: {e}")
        return False
    
    return True

def test_config():
    """Test configuration loading"""
    print("\n🧪 Testing configuration...")
    
    try:
        from config import settings, log_settings
        
        print(f"✅ Backup server: {settings.backup_server}")
        print(f"✅ Backup user: {settings.backup_user}")
        print(f"✅ Log level: {log_settings.log_level}")
        
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_logging():
    """Test logging setup"""
    print("\n🧪 Testing logging...")
    
    try:
        from logging_config import setup_logging, get_logger
        
        # Setup logging to temp directory
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            setup_logging(log_dir=tmp_dir, log_format="text")
            logger = get_logger("test")
            logger.info("Test log message")
            print("✅ Logging system works")
        
        return True
    except Exception as e:
        print(f"❌ Logging test failed: {e}")
        return False

def test_models():
    """Test data models"""
    print("\n🧪 Testing models...")
    
    try:
        from models import VMInfo, VMState, BackupJob, BackupMode
        from datetime import datetime
        
        # Test VM info
        vm = VMInfo(
            name="test-vm",
            uuid="test-uuid",
            state=VMState.RUNNING,
            memory_mb=1024,
            vcpus=2
        )
        print(f"✅ VM model: {vm.name} ({vm.state.value})")
        
        # Test backup job
        from backup_manager import BackupManager
        from config import settings
        
        backup_manager = BackupManager(settings)
        job = backup_manager.create_backup_job(
            name="test-job",
            vm_names=["test-vm"],
            mode=BackupMode.INCREMENTAL
        )
        print(f"✅ Backup job model: {job.name} ({job.mode.value})")
        
        return True
    except Exception as e:
        print(f"❌ Models test failed: {e}")
        return False

def test_ssh_client():
    """Test SSH client (dry run)"""
    print("\n🧪 Testing SSH client...")
    
    try:
        from ssh_client import SSHClient
        
        # Create client (don't connect)
        ssh = SSHClient("localhost", "user", password="pass")
        print("✅ SSH client created")
        
        return True
    except Exception as e:
        print(f"❌ SSH client test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 KVM Backup System - Test Suite")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_config,
        test_logging,
        test_models,
        test_ssh_client
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            failed += 1
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! System ready to use.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
