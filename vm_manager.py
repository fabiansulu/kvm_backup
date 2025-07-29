"""
Libvirt VM Manager with snapshot support
"""
import libvirt
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any
from datetime import datetime
import time
import os
from pathlib import Path

from models import VMInfo, VMState, SnapshotInfo
from logging_config import get_logger, LogOperation


class LibvirtManager:
    """Manager for libvirt operations with snapshot support"""
    
    def __init__(self, uri: str = "qemu:///system"):
        self.uri = uri
        self.conn: Optional[libvirt.virConnect] = None
        self.logger = get_logger("kvm_backup.vm_manager")
        
    def connect(self) -> bool:
        """Connect to libvirt daemon"""
        try:
            if self.conn is None or not self.conn.isAlive():
                self.conn = libvirt.open(self.uri)
                self.logger.info("Connected to libvirt", uri=self.uri)
                return True
            return True
        except libvirt.libvirtError as e:
            self.logger.error("Failed to connect to libvirt", uri=self.uri, error=str(e))
            return False
    
    def disconnect(self) -> None:
        """Disconnect from libvirt daemon"""
        if self.conn and self.conn.isAlive():
            self.conn.close()
            self.conn = None
            self.logger.info("Disconnected from libvirt")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    def list_all_vms(self) -> List[VMInfo]:
        """List all VMs (running and stopped)"""
        if not self.connect():
            return []
        
        try:
            vms = []
            domains = self.conn.listAllDomains()
            
            for domain in domains:
                vm_info = VMInfo.from_libvirt_domain(domain)
                vm_info.disk_paths = self._get_vm_disk_paths(domain)
                vm_info.config_path = self._get_vm_config_path(domain)
                vm_info.autostart = bool(domain.autostart())
                vms.append(vm_info)
                
            self.logger.info(f"Found {len(vms)} VMs", vm_count=len(vms))
            return vms
            
        except libvirt.libvirtError as e:
            self.logger.error("Failed to list VMs", error=str(e))
            return []
    
    def list_running_vms(self) -> List[VMInfo]:
        """List only running VMs"""
        all_vms = self.list_all_vms()
        return [vm for vm in all_vms if vm.state == VMState.RUNNING]
    
    def get_vm_by_name(self, name: str) -> Optional[VMInfo]:
        """Get VM information by name"""
        all_vms = self.list_all_vms()
        for vm in all_vms:
            if vm.name == name:
                return vm
        return None
    
    def _get_vm_disk_paths(self, domain) -> List[str]:
        """Extract disk paths from VM XML definition"""
        try:
            xml_desc = domain.XMLDesc()
            root = ET.fromstring(xml_desc)
            
            disk_paths = []
            for disk in root.findall(".//disk[@type='file']"):
                source = disk.find("source")
                if source is not None and source.get("file"):
                    disk_paths.append(source.get("file"))
                    
            return disk_paths
            
        except Exception as e:
            self.logger.warning(f"Failed to parse VM disks for {domain.name()}", error=str(e))
            return []
    
    def _get_vm_config_path(self, domain) -> Optional[str]:
        """Get VM configuration file path"""
        try:
            # Libvirt configs are typically in /etc/libvirt/qemu/
            config_path = f"/etc/libvirt/qemu/{domain.name()}.xml"
            if os.path.exists(config_path):
                return config_path
            return None
        except Exception:
            return None
    
    def create_snapshot(self, vm_name: str, snapshot_name: Optional[str] = None) -> Optional[SnapshotInfo]:
        """Create a snapshot of a VM"""
        if not self.connect():
            return None
        
        if snapshot_name is None:
            snapshot_name = f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        try:
            domain = self.conn.lookupByName(vm_name)
            
            with LogOperation(self.logger, "create_snapshot", vm_name=vm_name, snapshot_name=snapshot_name):
                # Create snapshot XML
                snapshot_xml = f"""
                <domainsnapshot>
                    <name>{snapshot_name}</name>
                    <description>Automated backup snapshot created at {datetime.now().isoformat()}</description>
                    <memory snapshot='external'/>
                    <disks>
                """
                
                # Add disk snapshots
                vm_xml = domain.XMLDesc()
                root = ET.fromstring(vm_xml)
                for disk in root.findall(".//disk[@type='file']"):
                    target = disk.find("target")
                    if target is not None:
                        dev = target.get("dev")
                        snapshot_xml += f'<disk name="{dev}" snapshot="external"/>'
                
                snapshot_xml += """
                    </disks>
                </domainsnapshot>
                """
                
                # Create the snapshot
                snapshot = domain.snapshotCreateXML(snapshot_xml, 
                    libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_DISK_ONLY |
                    libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_ATOMIC
                )
                
                snapshot_info = SnapshotInfo(
                    name=snapshot_name,
                    vm_name=vm_name,
                    creation_time=datetime.now(),
                    description=f"Backup snapshot for {vm_name}"
                )
                
                self.logger.info("Snapshot created successfully", 
                               vm_name=vm_name, snapshot_name=snapshot_name)
                return snapshot_info
                
        except libvirt.libvirtError as e:
            self.logger.error("Failed to create snapshot", 
                            vm_name=vm_name, snapshot_name=snapshot_name, error=str(e))
            return None
    
    def delete_snapshot(self, vm_name: str, snapshot_name: str) -> bool:
        """Delete a VM snapshot"""
        if not self.connect():
            return False
        
        try:
            domain = self.conn.lookupByName(vm_name)
            snapshot = domain.snapshotLookupByName(snapshot_name)
            
            with LogOperation(self.logger, "delete_snapshot", vm_name=vm_name, snapshot_name=snapshot_name):
                snapshot.delete(libvirt.VIR_DOMAIN_SNAPSHOT_DELETE_METADATA_ONLY)
                self.logger.info("Snapshot deleted successfully",
                               vm_name=vm_name, snapshot_name=snapshot_name)
                return True
                
        except libvirt.libvirtError as e:
            self.logger.error("Failed to delete snapshot",
                            vm_name=vm_name, snapshot_name=snapshot_name, error=str(e))
            return False
    
    def list_snapshots(self, vm_name: str) -> List[SnapshotInfo]:
        """List all snapshots for a VM"""
        if not self.connect():
            return []
        
        try:
            domain = self.conn.lookupByName(vm_name)
            snapshots = []
            
            for snapshot in domain.listAllSnapshots():
                snap_xml = snapshot.getXMLDesc()
                root = ET.fromstring(snap_xml)
                
                name = root.find("name").text if root.find("name") is not None else "unknown"
                desc_elem = root.find("description")
                description = desc_elem.text if desc_elem is not None else ""
                
                # Parse creation time
                creation_time_elem = root.find("creationTime")
                if creation_time_elem is not None:
                    creation_time = datetime.fromtimestamp(int(creation_time_elem.text))
                else:
                    creation_time = datetime.now()
                
                snapshot_info = SnapshotInfo(
                    name=name,
                    vm_name=vm_name,
                    creation_time=creation_time,
                    description=description
                )
                snapshots.append(snapshot_info)
            
            return snapshots
            
        except libvirt.libvirtError as e:
            self.logger.error("Failed to list snapshots", vm_name=vm_name, error=str(e))
            return []
    
    def shutdown_vm(self, vm_name: str, timeout: int = 60) -> bool:
        """Gracefully shutdown a VM"""
        if not self.connect():
            return False
        
        try:
            domain = self.conn.lookupByName(vm_name)
            
            if domain.state()[0] != libvirt.VIR_DOMAIN_RUNNING:
                self.logger.info("VM is not running", vm_name=vm_name)
                return True
            
            with LogOperation(self.logger, "shutdown_vm", vm_name=vm_name, timeout=timeout):
                # Request graceful shutdown
                domain.shutdown()
                
                # Wait for shutdown with timeout
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if domain.state()[0] != libvirt.VIR_DOMAIN_RUNNING:
                        self.logger.info("VM shutdown successfully", vm_name=vm_name)
                        return True
                    time.sleep(2)
                
                # Force shutdown if graceful failed
                self.logger.warning("Graceful shutdown timed out, forcing shutdown", vm_name=vm_name)
                domain.destroy()
                time.sleep(5)
                
                if domain.state()[0] != libvirt.VIR_DOMAIN_RUNNING:
                    self.logger.info("VM force shutdown successful", vm_name=vm_name)
                    return True
                else:
                    self.logger.error("Failed to shutdown VM", vm_name=vm_name)
                    return False
                    
        except libvirt.libvirtError as e:
            self.logger.error("Error during VM shutdown", vm_name=vm_name, error=str(e))
            return False
    
    def start_vm(self, vm_name: str) -> bool:
        """Start a VM"""
        if not self.connect():
            return False
        
        try:
            domain = self.conn.lookupByName(vm_name)
            
            if domain.state()[0] == libvirt.VIR_DOMAIN_RUNNING:
                self.logger.info("VM is already running", vm_name=vm_name)
                return True
            
            with LogOperation(self.logger, "start_vm", vm_name=vm_name):
                domain.create()
                self.logger.info("VM started successfully", vm_name=vm_name)
                return True
                
        except libvirt.libvirtError as e:
            self.logger.error("Failed to start VM", vm_name=vm_name, error=str(e))
            return False
    
    def export_vm_definition(self, vm_name: str, output_path: str) -> bool:
        """Export VM XML definition to file"""
        if not self.connect():
            return False
        
        try:
            domain = self.conn.lookupByName(vm_name)
            xml_desc = domain.XMLDesc()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(xml_desc)
            
            self.logger.info("VM definition exported", vm_name=vm_name, output_path=output_path)
            return True
            
        except (libvirt.libvirtError, IOError) as e:
            self.logger.error("Failed to export VM definition", 
                            vm_name=vm_name, output_path=output_path, error=str(e))
            return False
