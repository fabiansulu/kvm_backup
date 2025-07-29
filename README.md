# KVM Backup System

Une solution moderne de sauvegarde pour machines virtuelles KVM/libvirt, développée en Python.

## 🚀 Fonctionnalités

### Sauvegardes sans interruption de service
- **Snapshots libvirt** : Sauvegarde sans arrêter les VMs
- **Trois modes** : Complet, Incrémentiel, Synchronisation
- **Gestion d'erreurs robuste** avec restauration automatique
- **Logs structurés** JSON pour faciliter le debugging

### Interface moderne
- **CLI riche** avec Typer et Rich (couleurs, tableaux, barres de progression)
- **API REST** avec FastAPI pour intégration web
- **Configuration flexible** via fichiers YAML/JSON ou variables d'environnement

### Fonctionnalités avancées
- **Tests automatisés** avec pytest
- **Sauvegarde parallèle** de plusieurs VMs
- **Retention automatique** des anciennes sauvegardes
- **Scripts pré/post-sauvegarde** personnalisables
- **Métriques et monitoring** intégrés

## 📦 Installation

### Prérequis
```bash
# Dépendances système
sudo apt update
sudo apt install -y python3 python3-pip python3-venv libvirt-dev pkg-config
sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients

# Pour les transferts SSH
sudo apt install -y rsync sshpass
```

### Installation Python
```bash
cd /home/authentik/backup-kvm/app_backup_kvm

# Créer environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Rendre le script principal exécutable
chmod +x main.py
```

### Configuration
```bash
# Copier et adapter la configuration
cp .env.example .env
nano .env

# Créer le répertoire de logs
sudo mkdir -p /var/log/kvm-backup
sudo chown $USER:$USER /var/log/kvm-backup
```

## 🎯 Utilisation

### Interface en ligne de commande

#### Lister les VMs
```bash
# Toutes les VMs
./main.py list-vms

# Seulement les VMs en cours d'exécution avec détails
./main.py list-vms --running --details
```

#### Sauvegardes
```bash
# Sauvegarde incrémentielle (recommandée)
./main.py backup vm1 vm2 --mode incremental

# Sauvegarde complète
./main.py backup vm1 vm2 --mode full

# Test de sauvegarde (simulation)
./main.py backup vm1 vm2 --dry-run

# Sauvegarde sans snapshots (arrêt temporaire des VMs)
./main.py backup vm1 vm2 --no-snapshots

# Sauvegarde avec nom personnalisé
./main.py backup vm1 vm2 --name "sauvegarde-hebdomadaire"
```

#### Gestion des snapshots
```bash
# Lister les snapshots d'une VM
./main.py snapshots vm1 list

# Créer un snapshot manuel
./main.py snapshots vm1 create --name "avant-mise-a-jour"

# Supprimer un snapshot
./main.py snapshots vm1 delete --name "snapshot-ancien"
```

#### Configuration
```bash
# Afficher la configuration actuelle
./main.py config
```

### Interface Web API

#### Démarrer le serveur API
```bash
# Mode production
./main.py server

# Mode développement avec rechargement automatique
./main.py server --reload --host 127.0.0.1 --port 8080
```

#### Endpoints principaux

**VMs :**
- `GET /vms` - Lister toutes les VMs
- `GET /vms/{vm_name}` - Détails d'une VM
- `GET /vms?running_only=true` - VMs en cours d'exécution

**Sauvegardes :**
- `POST /backup` - Créer une tâche de sauvegarde
- `GET /backup` - Lister toutes les tâches
- `GET /backup/{job_id}` - État d'une tâche

**Snapshots :**
- `GET /snapshots/{vm_name}` - Lister les snapshots
- `POST /snapshots` - Créer un snapshot
- `DELETE /snapshots/{vm_name}/{snapshot_name}` - Supprimer

**Système :**
- `GET /health` - État du système
- `GET /stats` - Statistiques générales

#### Exemples d'utilisation de l'API

```bash
# Créer une sauvegarde via API
curl -X POST "http://localhost:8000/backup" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sauvegarde-api",
    "vm_names": ["vm1", "vm2"],
    "mode": "incremental",
    "dry_run": false,
    "use_snapshots": true
  }'

# Vérifier l'état
curl "http://localhost:8000/backup/job-id-retourné"

# Créer un snapshot
curl -X POST "http://localhost:8000/snapshots" \
  -H "Content-Type: application/json" \
  -d '{
    "vm_name": "vm1",
    "snapshot_name": "manual-snapshot"
  }'
```

## 🔧 Configuration avancée

### Modes de sauvegarde

#### Mode Incrémentiel (recommandé)
- Utilise rsync avec `--link-dest` pour économiser l'espace
- Transfert uniquement des données modifiées
- Structure : `latest/`, `previous/`, `archive/`

#### Mode Complet
- Sauvegarde complète horodatée
- Idéal pour archives long terme
- Structure : `YYYY-MM-DD_HH-MM-SS/`

#### Mode Synchronisation
- Maintient un miroir exact
- Supprime les fichiers qui n'existent plus
- Structure : `sync/`

### Scripts personnalisés

```bash
# Script pré-sauvegarde (exemple)
cat > /usr/local/bin/pre-backup.sh << 'EOF'
#!/bin/bash
echo "Nettoyage des logs temporaires..."
find /var/log -name "*.tmp" -delete
systemctl stop non-essential-service
EOF

chmod +x /usr/local/bin/pre-backup.sh

# Utilisation dans une sauvegarde
./main.py backup vm1 --pre-script /usr/local/bin/pre-backup.sh
```

### Configuration SSH avec clés

```bash
# Générer une clé SSH
ssh-keygen -t rsa -b 4096 -f ~/.ssh/kvm-backup-key

# Copier sur le serveur de sauvegarde
ssh-copy-id -i ~/.ssh/kvm-backup-key.pub authentik@192.168.26.27

# Configurer dans .env
echo "KVM_BACKUP_SSH_KEY_FILE=/home/$USER/.ssh/kvm-backup-key" >> .env
```

## 📊 Logs et Monitoring

### Logs structurés
```bash
# Suivre les logs en temps réel
tail -f /var/log/kvm-backup/kvm-backup.log

# Filtrer par VM
grep '"vm_name":"vm1"' /var/log/kvm-backup/kvm-backup.log | jq .

# Filtrer par erreurs
grep '"level":"ERROR"' /var/log/kvm-backup/kvm-backup.log | jq .
```

### Métriques
- Taille totale des sauvegardes
- Durée des opérations
- Taux de succès
- Utilisation disque

## 🧪 Tests

```bash
# Exécuter tous les tests
python -m pytest test_kvm_backup.py -v

# Tests avec couverture
pip install pytest-cov
python -m pytest --cov=app_backup_kvm test_kvm_backup.py

# Tests d'intégration uniquement
python -m pytest test_kvm_backup.py::TestIntegration -v
```

## 📅 Automatisation avec Cron

```bash
# Éditer le crontab
sudo crontab -e

# Sauvegardes automatiques
# Incrémentielle quotidienne à 2h
0 2 * * * /home/authentik/backup-kvm/app_backup_kvm/main.py backup vm1 vm2 vm3 --mode incremental

# Complète hebdomadaire le dimanche à 1h
0 1 * * 0 /home/authentik/backup-kvm/app_backup_kvm/main.py backup vm1 vm2 vm3 --mode full

# Nettoyage mensuel des anciens snapshots
0 3 1 * * /home/authentik/backup-kvm/app_backup_kvm/main.py cleanup-snapshots --older-than 30
```

## 🔒 Sécurité

### Bonnes pratiques
1. **Clés SSH** plutôt que mots de passe
2. **Répertoire de sauvegarde sécurisé** avec bonnes permissions
3. **Chiffrement des données** sensibles
4. **Rotation des logs** pour éviter l'accumulation
5. **Monitoring des échecs** avec alertes

### Permissions recommandées
```bash
# Sécuriser les fichiers de configuration
chmod 600 .env
chmod 600 ~/.ssh/kvm-backup-key

# Répertoires de sauvegarde
sudo mkdir -p /backup/kvm
sudo chown authentik:authentik /backup/kvm
sudo chmod 750 /backup/kvm
```

## 🆚 Avantages vs Script Bash original

| Fonctionnalité | Script Bash | Python App |
|---|---|---|
| **Snapshots sans arrêt VM** | ❌ | ✅ |
| **Interface web** | ❌ | ✅ |
| **API REST** | ❌ | ✅ |
| **Logs structurés** | ❌ | ✅ |
| **Tests automatisés** | ❌ | ✅ |
| **Gestion d'erreurs** | ⚠️ Basic | ✅ Robuste |
| **Configuration flexible** | ⚠️ Variables | ✅ Multi-format |
| **Parallélisation** | ❌ | ✅ |
| **Métriques** | ❌ | ✅ |
| **Facilité de maintenance** | ⚠️ | ✅ |

## 🎁 Interface Web Future

Le système est prêt pour une interface web complète :

### Frontend React/Vue.js
- Dashboard avec état des VMs
- Planification des sauvegardes
- Historique et logs visuels
- Monitoring en temps réel
- Gestion des snapshots

### Architecture suggérée
```
Frontend (React/Vue) → API REST (FastAPI) → Core Python → libvirt/SSH
```

## 🐛 Résolution de problèmes

### Erreurs communes

**Connexion libvirt échoue :**
```bash
# Vérifier le service
sudo systemctl status libvirtd

# Ajouter l'utilisateur au groupe libvirt
sudo usermod -a -G libvirt $USER
newgrp libvirt
```

**Erreur SSH :**
```bash
# Tester manuellement
ssh authentik@192.168.26.27

# Vérifier les clés
ssh-add -l
```

**Snapshots échouent :**
```bash
# Vérifier si la VM supporte les snapshots
virsh domblklist vm1
# Les disques doivent être en qcow2
```

## 📞 Support

- **Logs** : `/var/log/kvm-backup/`
- **Configuration** : `.env` dans le répertoire app
- **Tests** : `python -m pytest test_kvm_backup.py -v`
- **API docs** : `http://localhost:8000/docs` (quand le serveur tourne)

---

**Prêt pour la production !** 🚀

Cette version Python moderne remplace complètement votre script bash avec des fonctionnalités avancées et une architecture extensible pour une interface web future.
