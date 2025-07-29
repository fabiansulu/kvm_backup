# Guide de Configuration - KVM Backup System

## Démarrage rapide - Interface Web

### ✅ Méthode recommandée pour l'entreprise

**Démarrage du monitoring web :**
```bash
cd /home/authentik/backup-kvm
python3 app_backup_kvm/kvm_monitor.py
```

**Accès à l'interface :**
- **URL :** http://localhost:8080
- **Interface responsive** avec design entreprise
- **Monitoring temps réel** des VMs KVM
- **Gestion des snapshots** et sauvegardes

### Fonctionnalités disponibles

- 📊 **Dashboard en temps réel** avec statut système
- 💻 **Liste complète des VMs** avec état actuel  
- 📸 **Création de snapshots** en un clic
- 💾 **Gestion des sauvegardes** intégrée
- 🔄 **Actualisation automatique** toutes les 30 secondes

## Configuration avancée

### Méthode 1 : Fichier .env (Recommandée)

1. Éditez le fichier `.env` dans le répertoire app_backup_kvm :
```bash
nano /home/authentik/backup-kvm/app_backup_kvm/.env
```

2. Modifiez les valeurs selon vos besoins :
```bash
# Votre serveur de sauvegarde
BACKUP_SERVER=192.168.1.100
BACKUP_USER=monuser
BACKUP_PASSWORD=monmotdepasse

# Répertoires personnalisés
REMOTE_BACKUP_DIR=/mon/repertoire/backup
LOCAL_VM_DIR=/var/lib/libvirt/images
LOG_DIR=./logs

# SSH
SSH_PORT=22
SSH_TIMEOUT=30

# API Web
API_HOST=0.0.0.0
API_PORT=8000
```

### Méthode 2 : Variables d'environnement temporaires

```bash
# Pour une session
export BACKUP_SERVER="192.168.1.100"
export BACKUP_USER="monuser"
export BACKUP_PASSWORD="monmotdepasse"

# Puis lancer l'application
python3 cli.py config
```

### Méthode 3 : Modification directe du code

Éditez directement le fichier `config.py` :
```bash
nano /home/authentik/backup-kvm/app_backup_kvm/config.py
```

## Utilisation SANS sudo

```bash
# CORRECT - Activez l'environnement virtuel
cd /home/authentik/backup-kvm/app_backup_kvm
source venv/bin/activate

# Puis utilisez l'application
python3 cli.py config
python3 cli.py list-vms
```

## ✅ Interface Web Opérationnelle

### Serveur de monitoring KVM (Solution finale)

**Démarrage :**
```bash
cd /home/authentik/backup-kvm
python3 app_backup_kvm/kvm_monitor.py
```

**Caractéristiques :**
- 🚀 **Serveur HTTP Python natif** - aucune dépendance complexe
- 🔧 **Intégration directe virsh** pour KVM
- 📱 **Interface responsive** pour tous appareils
- 🔄 **Actualisation automatique** des données
- 🏢 **Design entreprise** professionnel

### Alternative FastAPI (pour développement avancé)

```bash
cd /home/authentik/backup-kvm/app_backup_kvm
source venv/bin/activate
uvicorn api:app --host 0.0.0.0 --port 8000
```

## Quand utiliser sudo

Sudo n'est nécessaire que pour :
- Accéder aux fichiers VMs dans /var/lib/libvirt/images
- Lire les configurations dans /etc/libvirt/qemu
- Opérations libvirt si l'utilisateur n'est pas dans le groupe libvirt

### Pour éviter sudo avec libvirt :
```bash
# Ajoutez votre utilisateur au groupe libvirt
sudo usermod -a -G libvirt authentik

# Puis redémarrez votre session ou exécutez :
newgrp libvirt
```

## État actuel du système (Juillet 2025)

## ✅ Statut du Système (Mise à jour 29 juillet 2025)

### 🎉 Fonctionnalités 100% opérationnelles :
- **Interface Web de Monitoring** : ✅ FONCTIONNELLE (http://localhost:8080)
- **Configuration** : ✅ Fonctionne parfaitement (python3 cli.py config)
- **Détection VMs** : ✅ Trouve correctement les VMs libvirt (mainserver, onlyoffice)
- **API REST** : ✅ Endpoints fonctionnels (/api/vms, /api/status, /api/snapshots)
- **Logging** : ✅ Système structuré JSON fonctionnel
- **Snapshots** : ✅ Implémentation libvirt prête
- **Design Entreprise** : ✅ Interface responsive professionnelle

### 🚀 Solution finale recommandée :
**Serveur de monitoring KVM simple et robuste**
```bash
cd /home/authentik/backup-kvm
python3 app_backup_kvm/kvm_monitor.py
# Interface accessible sur http://localhost:8080
```

### ⚠️ Solutions alternatives :
- **FastAPI** : Pour développement avancé (uvicorn api:app)
- **CLI Typer** : Quelques commandes peuvent nécessiter debug

## Test de la configuration

```bash
cd /home/authentik/backup-kvm/app_backup_kvm
source venv/bin/activate

# Tester la configuration
python3 cli.py config

# Vérifier les VMs
virsh list --all

# Démarrer l'API (méthode fiable)
uvicorn api:app --host 0.0.0.0 --port 8000
```

## Accès à l'interface web

### 🎯 Interface web graphique (nouvelle !) :
```
http://localhost:8000/ui
```
Interface web complète avec :
- Liste des VMs avec statut
- Création de snapshots en un clic
- Lancement de sauvegardes
- Gestion des snapshots

### 📚 Documentation interactive API :
```
http://localhost:8000/docs
```
Interface Swagger pour :
- Voir toutes les API disponibles
- Tester les endpoints directement
- Documentation complète

### 🔗 Endpoints JSON directs :
```
http://localhost:8000/              # Statut API (JSON)
http://localhost:8000/vms           # Liste des VMs (JSON)
http://localhost:8000/redoc         # Documentation alternative
```

## Debug et logs

```bash
# Voir les logs en temps réel
tail -f ./logs/kvm-backup.log

# Test direct des composants
python3 -c "from vm_manager import LibvirtManager; print('VM Manager OK')"
python3 -c "from api import app; print('API OK')"
```

## Sauvegarde manuelle (temporaire)

En attendant les corrections CLI, vous pouvez :

```bash
# Lister les VMs
virsh list --all

# Créer un snapshot
virsh snapshot-create-as nom_vm snapshot_$(date +%Y%m%d_%H%M%S)

# Lister les snapshots
virsh snapshot-list nom_vm

# Copier les disques manuellement
rsync -avz /var/lib/libvirt/images/vm.qcow2 user@backup-server:/backup/
```
