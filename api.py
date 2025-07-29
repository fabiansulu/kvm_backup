"""
FastAPI web interface for KVM backup system
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import asyncio
import uuid

from models import BackupJob, BackupResult, BackupMode, BackupStatus, VMInfo
from vm_manager import LibvirtManager  
from backup_manager import BackupManager
from config import settings
from logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger("kvm_backup.api")

# FastAPI app
app = FastAPI(
    title="KVM Backup API",
    description="Modern backup solution for KVM/libvirt virtual machines",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
backup_manager = BackupManager(settings)
active_jobs: Dict[str, BackupResult] = {}


# Pydantic models for API
from pydantic import BaseModel, Field

class VMInfoResponse(BaseModel):
    name: str
    uuid: str
    state: str
    memory_mb: int
    vcpus: int
    disk_paths: List[str]
    config_path: Optional[str]
    autostart: bool

class BackupJobRequest(BaseModel):
    name: str
    vm_names: List[str]
    mode: BackupMode = BackupMode.INCREMENTAL
    dry_run: bool = False
    use_snapshots: bool = True
    compress: bool = True
    scheduled_time: Optional[datetime] = None

class BackupJobResponse(BaseModel):
    id: str
    name: str
    mode: str
    vm_names: List[str]
    created_at: datetime
    dry_run: bool
    use_snapshots: bool
    compress: bool

class BackupResultResponse(BaseModel):
    job_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[float]
    vm_results: Dict[str, Any]
    total_size_bytes: int
    transferred_bytes: int
    error_message: Optional[str]
    success_rate: float

class SnapshotRequest(BaseModel):
    vm_name: str
    snapshot_name: Optional[str] = None

class SnapshotResponse(BaseModel):
    name: str
    vm_name: str
    creation_time: datetime
    description: str


# API Routes

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "KVM Backup API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/ui")
async def web_interface():
    """Serve the web interface"""
    html_content = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KVM Backup System - Enterprise</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .header {
            background: rgba(255,255,255,0.95);
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header h1 { color: #2c3e50; margin-bottom: 10px; }
        .header .subtitle { color: #7f8c8d; font-size: 14px; }
        .container {
            max-width: 1200px;
            margin: 20px auto;
            padding: 0 20px;
        }
        .status-card {
            background: rgba(255,255,255,0.95);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .status-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #007bff;
        }
        .status-item.success { border-left-color: #28a745; }
        .status-item.warning { border-left-color: #ffc107; }
        .status-item.danger { border-left-color: #dc3545; }
        .vm-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
        }
        .vm-card {
            background: rgba(255,255,255,0.95);
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .vm-card:hover { transform: translateY(-2px); }
        .vm-card.running { border-left: 5px solid #28a745; }
        .vm-card.stopped { border-left: 5px solid #dc3545; }
        .vm-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .vm-name { font-size: 18px; font-weight: bold; }
        .vm-status {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }
        .vm-status.running { background: #d4edda; color: #155724; }
        .vm-status.stopped { background: #f8d7da; color: #721c24; }
        .vm-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 15px;
            font-size: 14px;
        }
        .vm-detail { 
            background: #f8f9fa; 
            padding: 8px; 
            border-radius: 4px;
        }
        .btn-group {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
            font-weight: bold;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { transform: translateY(-1px); }
        .btn.primary { background: #007bff; color: white; }
        .btn.success { background: #28a745; color: white; }
        .btn.warning { background: #ffc107; color: #000; }
        .btn.danger { background: #dc3545; color: white; }
        .btn.info { background: #17a2b8; color: white; }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
            font-size: 16px;
        }
        .refresh-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            font-size: 20px;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            transition: all 0.2s;
        }
        .refresh-btn:hover { 
            background: #0056b3; 
            transform: rotate(180deg); 
        }
        .snapshots-list {
            background: #f8f9fa;
            margin-top: 10px;
            padding: 10px;
            border-radius: 5px;
            max-height: 200px;
            overflow-y: auto;
        }
        .snapshot-item {
            background: white;
            padding: 8px;
            margin: 5px 0;
            border-radius: 4px;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🖥️ KVM Backup System</h1>
        <div class="subtitle">Système de sauvegarde d'entreprise pour machines virtuelles</div>
    </div>
    
    <div class="container">
        <div class="status-card">
            <h3>📊 Statut du système</h3>
            <div id="system-status" class="status-grid">
                <div class="status-item">
                    <div>🔧 API</div>
                    <div id="api-status">Chargement...</div>
                </div>
                <div class="status-item">
                    <div>💻 VMs</div>
                    <div id="vm-count">-</div>
                </div>
                <div class="status-item">
                    <div>⚡ En cours</div>
                    <div id="running-count">-</div>
                </div>
                <div class="status-item">
                    <div>🕒 Dernière MAJ</div>
                    <div id="last-update">-</div>
                </div>
            </div>
        </div>

        <div class="status-card">
            <h3>💻 Machines Virtuelles</h3>
            <div id="vm-list" class="loading">Chargement des VMs...</div>
        </div>
    </div>

    <button class="refresh-btn" onclick="loadAll()" title="Actualiser">🔄</button>

    <script>
        let refreshInterval;

        async function loadSystemStatus() {
            try {
                const response = await fetch('/');
                const data = await response.json();
                document.getElementById('api-status').textContent = data.status;
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                
                // Update status item style
                const apiStatusEl = document.getElementById('api-status').parentElement;
                apiStatusEl.className = 'status-item ' + (data.status === 'running' ? 'success' : 'danger');
            } catch (error) {
                document.getElementById('api-status').textContent = 'Erreur';
                document.getElementById('api-status').parentElement.className = 'status-item danger';
            }
        }

        async function loadVMs() {
            try {
                const response = await fetch('/vms');
                const vms = await response.json();
                
                document.getElementById('vm-count').textContent = vms.length;
                const runningCount = vms.filter(vm => vm.state.toLowerCase() === 'running').length;
                document.getElementById('running-count').textContent = runningCount;
                
                // Update counter styles
                document.getElementById('vm-count').parentElement.className = 'status-item info';
                document.getElementById('running-count').parentElement.className = 'status-item ' + (runningCount > 0 ? 'success' : 'warning');
                
                if (vms.length === 0) {
                    document.getElementById('vm-list').innerHTML = '<div class="loading">Aucune VM trouvée</div>';
                    return;
                }

                const vmHtml = vms.map(vm => `
                    <div class="vm-card ${vm.state.toLowerCase()}">
                        <div class="vm-header">
                            <div class="vm-name">${vm.name}</div>
                            <div class="vm-status ${vm.state.toLowerCase()}">${vm.state}</div>
                        </div>
                        <div class="vm-details">
                            <div class="vm-detail"><strong>💾 Mémoire:</strong> ${vm.memory_mb} MB</div>
                            <div class="vm-detail"><strong>⚡ vCPUs:</strong> ${vm.vcpus}</div>
                            <div class="vm-detail"><strong>🆔 UUID:</strong> ${vm.uuid.substring(0,8)}...</div>
                            <div class="vm-detail"><strong>🔧 Autostart:</strong> ${vm.autostart ? 'Oui' : 'Non'}</div>
                        </div>
                        <div class="btn-group">
                            <button class="btn info" onclick="showSnapshots('${vm.name}')">📸 Snapshots</button>
                            <button class="btn success" onclick="backupVM('${vm.name}')">💾 Sauvegarder</button>
                            ${vm.state.toLowerCase() === 'running' ? 
                                '<button class="btn warning" onclick="createSnapshot(\\''+vm.name+'\\')">📷 Snapshot</button>' : 
                                '<button class="btn primary" onclick="startVM(\\''+vm.name+'\\')">▶️ Démarrer</button>'}
                        </div>
                        <div id="snapshots-${vm.name}" class="snapshots-list" style="display:none;"></div>
                    </div>
                `).join('');
                
                document.getElementById('vm-list').innerHTML = '<div class="vm-grid">' + vmHtml + '</div>';
            } catch (error) {
                document.getElementById('vm-list').innerHTML = '<div class="loading">❌ Erreur: ' + error.message + '</div>';
            }
        }

        async function showSnapshots(vmName) {
            const container = document.getElementById('snapshots-' + vmName);
            if (container.style.display === 'block') {
                container.style.display = 'none';
                return;
            }
            
            container.style.display = 'block';
            container.innerHTML = '<div class="loading">Chargement des snapshots...</div>';
            
            try {
                const response = await fetch('/vms/' + vmName + '/snapshots');
                const snapshots = await response.json();
                
                if (snapshots.length === 0) {
                    container.innerHTML = '<div class="snapshot-item">Aucun snapshot</div>';
                    return;
                }

                const snapshotHtml = snapshots.map(s => `
                    <div class="snapshot-item">
                        <div>
                            <strong>📸 ${s.name}</strong><br>
                            <small>🕒 ${new Date(s.creation_time).toLocaleString()}</small>
                        </div>
                        <button class="btn danger" onclick="deleteSnapshot('${vmName}', '${s.name}')" style="font-size:10px; padding:4px 8px;">🗑️</button>
                    </div>
                `).join('');
                
                container.innerHTML = snapshotHtml;
            } catch (error) {
                container.innerHTML = '<div class="snapshot-item">❌ Erreur: ' + error.message + '</div>';
            }
        }

        async function createSnapshot(vmName) {
            const snapshotName = 'backup_' + new Date().toISOString().slice(0,19).replace(/[:-]/g,'');
            try {
                const response = await fetch('/vms/' + vmName + '/snapshots', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: snapshotName })
                });
                
                if (response.ok) {
                    alert('✅ Snapshot créé: ' + snapshotName);
                    showSnapshots(vmName);
                } else {
                    const error = await response.json();
                    alert('❌ Erreur: ' + (error.detail || 'Erreur inconnue'));
                }
            } catch (error) {
                alert('❌ Erreur réseau: ' + error.message);
            }
        }

        async function backupVM(vmName) {
            if (!confirm('Démarrer la sauvegarde de "' + vmName + '" ?')) return;
            
            try {
                const response = await fetch('/backup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        name: 'backup_' + vmName + '_' + Date.now(),
                        vm_names: [vmName],
                        mode: 'snapshot',
                        use_snapshots: true
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    alert('✅ Sauvegarde démarrée !\\nJob ID: ' + result.id);
                } else {
                    const error = await response.json();
                    alert('❌ Erreur: ' + (error.detail || 'Erreur inconnue'));
                }
            } catch (error) {
                alert('❌ Erreur réseau: ' + error.message);
            }
        }

        function loadAll() {
            loadSystemStatus();
            loadVMs();
        }

        // Chargement initial et actualisation automatique
        document.addEventListener('DOMContentLoaded', function() {
            loadAll();
            refreshInterval = setInterval(loadAll, 30000); // 30 secondes
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test libvirt connection
        with LibvirtManager() as vm_manager:
            vms = vm_manager.list_all_vms()
            vm_count = len(vms)
        
        return {
            "status": "healthy",
            "libvirt": "connected",
            "vm_count": vm_count,
            "active_jobs": len(active_jobs),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/vms", response_model=List[VMInfoResponse])
async def list_vms(running_only: bool = False):
    """List all virtual machines"""
    try:
        with LibvirtManager() as vm_manager:
            if running_only:
                vms = vm_manager.list_running_vms()
            else:
                vms = vm_manager.list_all_vms()
        
        return [
            VMInfoResponse(
                name=vm.name,
                uuid=vm.uuid,
                state=vm.state.value,
                memory_mb=vm.memory_mb,
                vcpus=vm.vcpus,
                disk_paths=vm.disk_paths,
                config_path=vm.config_path,
                autostart=vm.autostart
            ) for vm in vms
        ]
    except Exception as e:
        logger.error("Failed to list VMs", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vms/{vm_name}", response_model=VMInfoResponse)
async def get_vm(vm_name: str):
    """Get specific VM information"""
    try:
        with LibvirtManager() as vm_manager:
            vm = vm_manager.get_vm_by_name(vm_name)
            
        if not vm:
            raise HTTPException(status_code=404, detail=f"VM '{vm_name}' not found")
        
        return VMInfoResponse(
            name=vm.name,
            uuid=vm.uuid,
            state=vm.state.value,
            memory_mb=vm.memory_mb,
            vcpus=vm.vcpus,
            disk_paths=vm.disk_paths,
            config_path=vm.config_path,
            autostart=vm.autostart
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get VM info", vm_name=vm_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/backup", response_model=BackupJobResponse)
async def create_backup_job(job_request: BackupJobRequest, background_tasks: BackgroundTasks):
    """Create and start a backup job"""
    try:
        # Validate VMs exist
        with LibvirtManager() as vm_manager:
            all_vms = [vm.name for vm in vm_manager.list_all_vms()]
            invalid_vms = set(job_request.vm_names) - set(all_vms)
            
        if invalid_vms:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid VM names: {', '.join(invalid_vms)}"
            )
        
        # Create backup job
        job = backup_manager.create_backup_job(
            name=job_request.name,
            vm_names=job_request.vm_names,
            mode=job_request.mode,
            scheduled_time=job_request.scheduled_time,
            dry_run=job_request.dry_run,
            use_snapshots=job_request.use_snapshots,
            compress=job_request.compress
        )
        
        # Start backup in background
        background_tasks.add_task(execute_backup_job, job)
        
        logger.info("Backup job created via API", job_id=job.id, vm_names=job.vm_names)
        
        return BackupJobResponse(
            id=job.id,
            name=job.name,
            mode=job.mode.value,
            vm_names=job.vm_names,
            created_at=job.created_at,
            dry_run=job.dry_run,
            use_snapshots=job.use_snapshots,
            compress=job.compress
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create backup job", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/backup/{job_id}", response_model=BackupResultResponse)
async def get_backup_status(job_id: str):
    """Get backup job status"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    result = active_jobs[job_id]
    
    return BackupResultResponse(
        job_id=result.job_id,
        status=result.status.value,
        start_time=result.start_time,
        end_time=result.end_time,
        duration_seconds=result.duration_seconds,
        vm_results=result.vm_results,
        total_size_bytes=result.total_size_bytes,
        transferred_bytes=result.transferred_bytes,
        error_message=result.error_message,
        success_rate=result.success_rate
    )

@app.get("/backup", response_model=List[BackupResultResponse])
async def list_backup_jobs():
    """List all backup jobs"""
    return [
        BackupResultResponse(
            job_id=result.job_id,
            status=result.status.value,
            start_time=result.start_time,
            end_time=result.end_time,
            duration_seconds=result.duration_seconds,
            vm_results=result.vm_results,
            total_size_bytes=result.total_size_bytes,
            transferred_bytes=result.transferred_bytes,
            error_message=result.error_message,
            success_rate=result.success_rate
        ) for result in active_jobs.values()
    ]

@app.post("/snapshots", response_model=SnapshotResponse)
async def create_snapshot(snapshot_request: SnapshotRequest):
    """Create a VM snapshot"""
    try:
        with LibvirtManager() as vm_manager:
            snapshot = vm_manager.create_snapshot(
                snapshot_request.vm_name,
                snapshot_request.snapshot_name
            )
            
        if not snapshot:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create snapshot for VM '{snapshot_request.vm_name}'"
            )
        
        logger.info("Snapshot created via API", 
                   vm_name=snapshot_request.vm_name, snapshot_name=snapshot.name)
        
        return SnapshotResponse(
            name=snapshot.name,
            vm_name=snapshot.vm_name,
            creation_time=snapshot.creation_time,
            description=snapshot.description
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create snapshot", 
                    vm_name=snapshot_request.vm_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/snapshots/{vm_name}", response_model=List[SnapshotResponse])
async def list_snapshots(vm_name: str):
    """List snapshots for a VM"""
    try:
        with LibvirtManager() as vm_manager:
            snapshots = vm_manager.list_snapshots(vm_name)
        
        return [
            SnapshotResponse(
                name=snap.name,
                vm_name=snap.vm_name,
                creation_time=snap.creation_time,
                description=snap.description
            ) for snap in snapshots
        ]
    except Exception as e:
        logger.error("Failed to list snapshots", vm_name=vm_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/snapshots/{vm_name}/{snapshot_name}")
async def delete_snapshot(vm_name: str, snapshot_name: str):
    """Delete a VM snapshot"""
    try:
        with LibvirtManager() as vm_manager:
            success = vm_manager.delete_snapshot(vm_name, snapshot_name)
            
        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete snapshot '{snapshot_name}' for VM '{vm_name}'"
            )
        
        logger.info("Snapshot deleted via API", vm_name=vm_name, snapshot_name=snapshot_name)
        
        return {"message": f"Snapshot '{snapshot_name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete snapshot", 
                    vm_name=vm_name, snapshot_name=snapshot_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        with LibvirtManager() as vm_manager:
            all_vms = vm_manager.list_all_vms()
            running_vms = vm_manager.list_running_vms()
        
        stats = {
            "vm_stats": {
                "total_vms": len(all_vms),
                "running_vms": len(running_vms),
                "stopped_vms": len(all_vms) - len(running_vms)
            },
            "backup_stats": {
                "active_jobs": len(active_jobs),
                "completed_jobs": len([j for j in active_jobs.values() 
                                     if j.status == BackupStatus.COMPLETED]),
                "failed_jobs": len([j for j in active_jobs.values() 
                                  if j.status == BackupStatus.FAILED])
            },
            "system_info": {
                "backup_server": settings.backup_server,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return stats
    except Exception as e:
        logger.error("Failed to get stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Background task functions
async def execute_backup_job(job: BackupJob):
    """Execute backup job in background"""
    try:
        # Initialize result
        result = BackupResult(
            job_id=job.id,
            status=BackupStatus.RUNNING,
            start_time=datetime.now()
        )
        active_jobs[job.id] = result
        
        # Execute backup
        result = await backup_manager.execute_backup(job)
        active_jobs[job.id] = result
        
        logger.info("Background backup job completed", 
                   job_id=job.id, status=result.status.value)
        
    except Exception as e:
        logger.error("Background backup job failed", job_id=job.id, error=str(e))
        # Update result with error
        if job.id in active_jobs:
            active_jobs[job.id].status = BackupStatus.FAILED
            active_jobs[job.id].error_message = str(e)
            active_jobs[job.id].end_time = datetime.now()


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("KVM Backup API starting up")
    
    # Test libvirt connection
    try:
        with LibvirtManager() as vm_manager:
            vms = vm_manager.list_all_vms()
            logger.info("Libvirt connection successful", vm_count=len(vms))
    except Exception as e:
        logger.error("Libvirt connection failed at startup", error=str(e))


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("KVM Backup API shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
