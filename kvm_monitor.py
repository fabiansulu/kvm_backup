#!/usr/bin/env python3
"""
Interface web simple pour KVM Backup System - ENTREPRISE
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import threading
import time
import os
import sys
from datetime import datetime
import urllib.parse

# Ajouter le répertoire parent au path pour importer les modules
sys.path.append('/home/authentik/backup-kvm/app_backup_kvm')

# Importer les modules du système de backup
try:
    from config import settings
    from backup_manager import BackupManager
    from models import BackupMode
    backup_system_available = True
except ImportError as e:
    print(f"Attention: modules backup non disponibles: {e}")
    BackupManager = None
    backup_system_available = False

# Global storage for backup jobs
backup_jobs = {}
job_counter = 0

class BackupJob:
    def __init__(self, job_id, vm_name, job_type="backup"):
        self.job_id = job_id
        self.vm_name = vm_name
        self.job_type = job_type
        self.status = "starting"  # starting, running, completed, failed
        self.progress = 0  # 0-100
        self.start_time = datetime.now()
        self.end_time = None
        self.current_step = "Initialisation..."
        self.error_message = None
        
    def to_dict(self):
        return {
            'job_id': self.job_id,
            'vm_name': self.vm_name,
            'job_type': self.job_type,
            'status': self.status,
            'progress': self.progress,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'current_step': self.current_step,
            'error_message': self.error_message,
            'duration': (datetime.now() - self.start_time).total_seconds() if not self.end_time else (self.end_time - self.start_time).total_seconds()
        }

class KVMMonitorHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        # Clean path to remove query parameters
        clean_path = self.path.split('?')[0]
        
        if clean_path == '/':
            self.serve_dashboard()
        elif clean_path == '/api/vms':
            self.serve_vms_json()
        elif clean_path == '/api/status':
            self.serve_status_json()
        elif clean_path == '/api/jobs':
            self.serve_jobs_json()
        elif clean_path.startswith('/api/jobs/'):
            job_id = clean_path.split('/')[-1]
            self.serve_job_detail_json(job_id)
        elif clean_path.startswith('/api/snapshots/'):
            vm_name = clean_path.split('/')[-1]
            self.serve_snapshots_json(vm_name)
        else:
            self.send_error(404)
    
    def do_POST(self):
        # Clean path to remove query parameters
        clean_path = self.path.split('?')[0]
        
        if clean_path.startswith('/api/snapshot/'):
            vm_name = clean_path.split('/')[-1]
            self.create_snapshot(vm_name)
        elif clean_path.startswith('/api/backup/'):
            vm_name = clean_path.split('/')[-1]
            self.backup_vm(vm_name)
        else:
            self.send_error(404)
    
    def serve_dashboard(self):
        html = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KVM Backup Monitor - Enterprise</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; color: #333;
        }
        .header {
            background: rgba(255,255,255,0.95); padding: 20px; text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header h1 { color: #2c3e50; margin-bottom: 10px; }
        .subtitle { color: #7f8c8d; font-size: 14px; }
        .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
        .status-card {
            background: rgba(255,255,255,0.95); border-radius: 10px; padding: 20px;
            margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .status-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px; margin-top: 15px;
        }
        .status-item {
            background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;
            border-left: 4px solid #007bff;
        }
        .status-item.success { border-left-color: #28a745; }
        .status-item.warning { border-left-color: #ffc107; }
        .status-item.danger { border-left-color: #dc3545; }
        .status-item.info { border-left-color: #17a2b8; }
        .vm-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
        .job-item {
            background: rgba(255,255,255,0.95); border-radius: 8px; padding: 15px; margin: 10px 0;
            border-left: 4px solid #007bff; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .job-item.running { border-left-color: #17a2b8; }
        .job-item.completed { border-left-color: #28a745; }
        .job-item.failed { border-left-color: #dc3545; }
        .progress-bar {
            width: 100%; height: 8px; background: #e9ecef; border-radius: 4px; overflow: hidden; margin: 8px 0;
        }
        .progress-fill {
            height: 100%; background: linear-gradient(90deg, #007bff, #17a2b8); transition: width 0.3s ease;
        }
        .progress-fill.completed { background: linear-gradient(90deg, #28a745, #20c997); }
        .progress-fill.failed { background: linear-gradient(90deg, #dc3545, #e74c3c); }
        .vm-card {
            background: rgba(255,255,255,0.95); border-radius: 10px; padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1); transition: transform 0.2s;
        }
        .vm-card:hover { transform: translateY(-2px); }
        .vm-card.running { border-left: 5px solid #28a745; }
        .vm-card.stopped { border-left: 5px solid #dc3545; }
        .vm-header {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;
        }
        .vm-name { font-size: 18px; font-weight: bold; }
        .vm-status {
            padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold;
            text-transform: uppercase;
        }
        .vm-status.running { background: #d4edda; color: #155724; }
        .vm-status.stopped { background: #f8d7da; color: #721c24; }
        .btn {
            padding: 8px 16px; border: none; border-radius: 5px; cursor: pointer;
            font-size: 12px; font-weight: bold; margin: 5px; transition: all 0.2s;
        }
        .btn:hover { transform: translateY(-1px); }
        .btn.success { background: #28a745; color: white; }
        .btn.warning { background: #ffc107; color: #000; }
        .btn.info { background: #17a2b8; color: white; }
        .refresh-btn {
            position: fixed; bottom: 20px; right: 20px; background: #007bff; color: white;
            border: none; border-radius: 50%; width: 60px; height: 60px; font-size: 20px;
            cursor: pointer; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .refresh-btn:hover { background: #0056b3; transform: rotate(180deg); }
        .loading { text-align: center; padding: 40px; color: #666; font-size: 16px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🖥️ KVM Backup Monitor</h1>
        <div class="subtitle">Système de surveillance et sauvegarde des KVM</div>
        <div id="current-time"></div>
    </div>
    
    <div class="container">
        <div class="status-card">
            <h3>📊 Statut du système</h3>
            <div class="status-grid">
                <div class="status-item success">
                    <div>🔧 Système</div>
                    <div id="system-status">Opérationnel</div>
                </div>
                <div class="status-item" id="vm-count-card">
                    <div>💻 VMs Total</div>
                    <div id="vm-count">-</div>
                </div>
                <div class="status-item" id="running-count-card">
                    <div>⚡ En cours</div>
                    <div id="running-count">-</div>
                </div>
                <div class="status-item" id="jobs-count-card">
                    <div>� Tâches actives</div>
                    <div id="jobs-count">-</div>
                </div>
                <div class="status-item">
                    <div>�🕒 Dernière MAJ</div>
                    <div id="last-update">-</div>
                </div>
            </div>
        </div>

        <div class="status-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3>📈 Tâches de sauvegarde</h3>
                <button class="btn info" onclick="loadJobs()">🔄 Actualiser</button>
            </div>
            <div id="jobs-list" class="loading">Chargement des tâches...</div>
        </div>

        <div class="status-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3>💻 Machines Virtuelles</h3>
                <button class="btn info" onclick="loadVMs()">🔄 Actualiser</button>
            </div>
            <div id="vm-list" class="loading">Chargement des VMs...</div>
        </div>
    </div>

    <button class="refresh-btn" onclick="loadAll()" title="Actualiser tout">🔄</button>

    <script>
        function updateTime() {
            document.getElementById('current-time').textContent = new Date().toLocaleString();
        }

        async function loadVMs() {
            try {
                const response = await fetch('/api/vms');
                const vms = await response.json();
                
                document.getElementById('vm-count').textContent = vms.length;
                const runningCount = vms.filter(vm => vm.state === 'running').length;
                document.getElementById('running-count').textContent = runningCount;
                
                // Update styles
                document.getElementById('vm-count-card').className = 'status-item info';
                document.getElementById('running-count-card').className = 'status-item ' + (runningCount > 0 ? 'success' : 'warning');
                
                if (vms.length === 0) {
                    document.getElementById('vm-list').innerHTML = '<div class="loading">Aucune VM trouvée</div>';
                    return;
                }

                const vmHtml = vms.map(vm => `
                    <div class="vm-card ${vm.state}">
                        <div class="vm-header">
                            <div class="vm-name">${vm.name}</div>
                            <div class="vm-status ${vm.state}">${vm.state}</div>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <div><strong>UUID:</strong> ${vm.uuid}</div>
                            <div><strong>Fichiers disque:</strong> ${vm.disks || 'N/A'}</div>
                        </div>
                        <div>
                            <button class="btn info" onclick="showSnapshots('${vm.name}')">📸 Snapshots</button>
                            <button class="btn success" onclick="backupVM('${vm.name}')">💾 Sauvegarder</button>
                            ${vm.state === 'running' ? 
                                '<button class="btn warning" onclick="createSnapshot(\\''+vm.name+'\\')">📷 Snapshot</button>' : ''}
                        </div>
                        <div id="snapshots-${vm.name}" style="margin-top: 10px; display: none;"></div>
                    </div>
                `).join('');
                
                document.getElementById('vm-list').innerHTML = '<div class="vm-grid">' + vmHtml + '</div>';
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
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
            container.innerHTML = '<div style="padding: 10px;">Chargement des snapshots...</div>';
            
            try {
                const response = await fetch('/api/snapshots/' + vmName);
                const snapshots = await response.json();
                
                if (snapshots.length === 0) {
                    container.innerHTML = '<div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">Aucun snapshot</div>';
                    return;
                }

                const snapshotHtml = snapshots.map(s => `
                    <div style="background: #f8f9fa; padding: 8px; margin: 5px 0; border-radius: 4px; font-size: 12px;">
                        📸 <strong>${s.name}</strong> - ${s.date}
                    </div>
                `).join('');
                
                container.innerHTML = snapshotHtml;
            } catch (error) {
                container.innerHTML = '<div style="padding: 10px; color: red;">❌ Erreur: ' + error.message + '</div>';
            }
        }

        async function loadJobs() {
            try {
                const response = await fetch('/api/jobs');
                const jobs = await response.json();
                
                document.getElementById('jobs-count').textContent = jobs.filter(j => j.status === 'running').length;
                document.getElementById('jobs-count-card').className = 'status-item ' + 
                    (jobs.filter(j => j.status === 'running').length > 0 ? 'info' : 'success');
                
                if (jobs.length === 0) {
                    document.getElementById('jobs-list').innerHTML = '<div class="loading">Aucune tâche en cours</div>';
                    return;
                }

                const jobsHtml = jobs.map(job => `
                    <div class="job-item ${job.status}">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div style="font-weight: bold;">
                                ${job.job_type === 'backup' ? '💾' : '📸'} ${job.vm_name} - ${job.job_type}
                            </div>
                            <div style="font-size: 12px; color: #666;">
                                Job #${job.job_id} | ${Math.round(job.duration)}s
                            </div>
                        </div>
                        <div style="font-size: 12px; color: #666; margin-bottom: 8px;">
                            ${job.current_step}
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill ${job.status}" style="width: ${job.progress}%;"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 11px; color: #666;">
                            <span>Statut: <strong>${getStatusText(job.status)}</strong></span>
                            <span>${job.progress}%</span>
                        </div>
                        ${job.error_message ? '<div style="color: red; font-size: 11px; margin-top: 5px;">❌ ' + job.error_message + '</div>' : ''}
                    </div>
                `).join('');
                
                document.getElementById('jobs-list').innerHTML = jobsHtml;
            } catch (error) {
                document.getElementById('jobs-list').innerHTML = '<div class="loading">❌ Erreur: ' + error.message + '</div>';
            }
        }

        function getStatusText(status) {
            const statusMap = {
                'starting': '🔄 Démarrage',
                'running': '⚡ En cours',
                'completed': '✅ Terminé',
                'failed': '❌ Échec'
            };
            return statusMap[status] || status;
        }

        async function createSnapshot(vmName) {
            const snapshotName = 'backup_' + new Date().toISOString().slice(0,19).replace(/[:-]/g,'');
            try {
                const response = await fetch('/api/snapshot/' + vmName, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: snapshotName })
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('✅ Snapshot créé: ' + snapshotName);
                    showSnapshots(vmName);
                } else {
                    alert('❌ Erreur: ' + result.error);
                }
            } catch (error) {
                alert('❌ Erreur réseau: ' + error.message);
            }
        }

        async function backupVM(vmName) {
            if (!confirm('Démarrer la sauvegarde de "' + vmName + '" ?')) return;
            
            try {
                const response = await fetch('/api/backup/' + vmName, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('✅ Sauvegarde démarrée pour ' + vmName + ' (Job #' + result.job_id + ')');
                    loadJobs(); // Actualiser la liste des tâches
                } else {
                    alert('❌ Erreur: ' + result.error);
                }
            } catch (error) {
                alert('❌ Erreur réseau: ' + error.message);
            }
        }

        function loadAll() {
            loadVMs();
            loadJobs();
            updateTime();
        }

        // Chargement initial et actualisation
        document.addEventListener('DOMContentLoaded', function() {
            loadAll();
            setInterval(updateTime, 1000);
            setInterval(loadVMs, 30000); // 30 secondes
            setInterval(loadJobs, 5000);  // 5 secondes pour les tâches
        });
    </script>

    <footer style="text-align: center; margin-top: 40px; padding: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
        <p style="font-size: 9px; color: rgba(255,255,255,0.6); margin: 0;">
            par <a href="https://www.fabiansulu.com" target="_blank" style="color: rgba(255,255,255,0.6); text-decoration: none;">Authentik</a>
        </p>
    </footer>

</body>
</html>
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_vms_json(self):
        try:
            result = subprocess.run(['virsh', 'list', '--all'], capture_output=True, text=True)
            vms = []
            
            for line in result.stdout.split('\n')[2:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        vm_id = parts[0] if parts[0] != '-' else None
                        vm_name = parts[1]
                        vm_state = ' '.join(parts[2:]) if len(parts) > 2 else 'unknown'
                        
                        # Get UUID
                        uuid_result = subprocess.run(['virsh', 'domuuid', vm_name], capture_output=True, text=True)
                        vm_uuid = uuid_result.stdout.strip() if uuid_result.returncode == 0 else 'unknown'
                        
                        vms.append({
                            'name': vm_name,
                            'state': vm_state.replace('shut off', 'stopped'),
                            'uuid': vm_uuid,
                            'disks': 'N/A'  # Simplified for now
                        })
            
            self.send_json_response(vms)
        except Exception as e:
            self.send_json_response({'error': str(e)})
    
    def serve_status_json(self):
        self.send_json_response({
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'service': 'KVM Backup Monitor'
        })
    
    def serve_jobs_json(self):
        global backup_jobs
        jobs_list = [job.to_dict() for job in backup_jobs.values()]
        # Trier par date de début (plus récent en premier)
        jobs_list.sort(key=lambda x: x['start_time'], reverse=True)
        # Garder seulement les 20 dernières tâches
        self.send_json_response(jobs_list[:20])
    
    def serve_job_detail_json(self, job_id):
        global backup_jobs
        if job_id in backup_jobs:
            self.send_json_response(backup_jobs[job_id].to_dict())
        else:
            self.send_json_response({'error': 'Job not found'})
    
    def serve_snapshots_json(self, vm_name):
        try:
            result = subprocess.run(['virsh', 'snapshot-list', vm_name], capture_output=True, text=True)
            snapshots = []
            
            for line in result.stdout.split('\n')[2:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        snapshots.append({
                            'name': parts[0],
                            'date': ' '.join(parts[1:3]) if len(parts) >= 3 else parts[1]
                        })
            
            self.send_json_response(snapshots)
        except Exception as e:
            self.send_json_response({'error': str(e)})
    
    def create_snapshot(self, vm_name):
        try:
            snapshot_name = f"backup_{int(time.time())}"
            result = subprocess.run(['virsh', 'snapshot-create-as', vm_name, snapshot_name], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                self.send_json_response({'success': True, 'snapshot': snapshot_name})
            else:
                self.send_json_response({'success': False, 'error': result.stderr})
        except Exception as e:
            self.send_json_response({'success': False, 'error': str(e)})
    
    def backup_vm(self, vm_name):
        global backup_jobs, job_counter
        job_counter += 1
        job_id = str(job_counter)
        
        # Créer une nouvelle tâche
        job = BackupJob(job_id, vm_name, "backup")
        backup_jobs[job_id] = job
        
        # Démarrer la tâche en arrière-plan
        def run_backup():
            try:
                job.status = "running"
                job.current_step = "Chargement de la configuration..."
                job.progress = 5
                time.sleep(1)
                
                # Charger la configuration pour le transfert SSH
                if backup_system_available:
                    try:
                        config = settings  # Utiliser les settings globaux
                        backup_manager = BackupManager(config)
                        job.current_step = "Configuration chargée - mode entreprise activé"
                        job.progress = 10
                        time.sleep(1)
                        
                        # Utiliser le vrai système de backup
                        job.current_step = "Création du snapshot KVM..."
                        job.progress = 20
                        
                        # Créer un job de backup via le système principal
                        backup_job = backup_manager.create_backup_job(
                            name=f"web_backup_{vm_name}_{int(time.time())}",
                            vm_names=[vm_name],
                            mode=BackupMode.SNAPSHOT
                        )
                        
                        job.progress = 30
                        job.current_step = "Exécution de la sauvegarde avec transfert SSH..."
                        
                        # Exécuter la sauvegarde (asynchrone)
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        async def run_async_backup():
                            result = await backup_manager.execute_backup(backup_job)
                            return result
                        
                        backup_result = loop.run_until_complete(run_async_backup())
                        loop.close()
                        
                        job.progress = 90
                        job.current_step = "Finalisation du transfert..."
                        time.sleep(1)
                        
                        if backup_result.status.value == "completed":
                            job.progress = 100
                            job.status = "completed"
                            job.current_step = f"Sauvegarde transférée vers {config.backup_server} avec succès!"
                        else:
                            job.status = "failed"
                            job.error_message = f"Échec backup: {backup_result.error_message or 'Erreur inconnue'}"
                        
                    except Exception as e:
                        job.progress = 15
                        job.current_step = f"Système entreprise indisponible, mode snapshot simple..."
                        time.sleep(1)
                        # Fallback vers snapshot simple
                        self._simple_snapshot_backup(job, vm_name)
                else:
                    # Mode fallback : snapshot simple sans transfert
                    job.current_step = "Mode snapshot simple (pas de transfert SSH)"
                    job.progress = 15
                    self._simple_snapshot_backup(job, vm_name)
                    
                job.end_time = datetime.now()
                
            except Exception as e:
                job.status = "failed"
                job.error_message = str(e)
                job.end_time = datetime.now()
        
        # Lancer en thread
        thread = threading.Thread(target=run_backup, daemon=True)
        thread.start()
        
        self.send_json_response({'success': True, 'job_id': job_id, 'message': f'Backup started for {vm_name}'})
    
    def _simple_snapshot_backup(self, job, vm_name):
        """Backup simple avec snapshot seulement (fallback)"""
        try:
            job.current_step = "Création du snapshot local..."
            job.progress = 30
            time.sleep(1)
            
            # Créer le snapshot
            snapshot_name = f"backup_{int(time.time())}"
            result = subprocess.run(['virsh', 'snapshot-create-as', vm_name, snapshot_name], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                job.status = "failed"
                job.error_message = f"Échec création snapshot: {result.stderr}"
                return
            
            job.progress = 70
            job.current_step = "Snapshot créé (mode local uniquement)"
            time.sleep(1)
            
            job.progress = 100
            job.status = "completed"
            job.current_step = f"Snapshot local créé: {snapshot_name} (pas de transfert SSH configuré)"
            
        except Exception as e:
            job.status = "failed"
            job.error_message = f"Erreur snapshot: {str(e)}"
    
    
    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

def start_monitor_server(port=8080):
    server = HTTPServer(('0.0.0.0', port), KVMMonitorHandler)
    print(f"🚀 KVM Backup Monitor démarré sur http://0.0.0.0:{port}")
    print(f"📊 Interface de monitoring: http://localhost:{port}")
    print("🔧 Système opérationnel pour entreprise")
    server.serve_forever()

if __name__ == '__main__':
    start_monitor_server()
