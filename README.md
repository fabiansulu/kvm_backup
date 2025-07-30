# KVM Backup System

Une solution moderne et complète de sauvegarde pour machines virtuelles KVM/libvirt, développée en Python avec interface web de monitoring et planification automatique.

## 🚀 Fonctionnalités Principales

### 💾 Sauvegardes Avancées
- **Snapshots libvirt** : Sauvegarde sans arrêter les VMs
- **Trois modes** : Complet, Incrémentiel, Synchronisation
- **Transfert SSH** automatique vers serveur distant
- **Gestion d'erreurs robuste** avec restauration automatique
- **Logs structurés** JSON pour faciliter le debugging

### ⏰ Planification Automatique - NOUVEAU !
- **Sauvegardes programmées** : Quotidiennes, hebdomadaires, mensuelles
- **Interface web intuitive** pour créer et gérer les planifications
- **CLI professionnel** pour administration avancée
- **Scheduler intégré** avec exécution automatique en arrière-plan
- **Monitoring temps réel** des tâches programmées

### 🌐 Interface Moderne
- **Dashboard web** responsive avec design entreprise
- **Monitoring temps réel** des VMs et sauvegardes
- **CLI riche** avec Typer et Rich (couleurs, tableaux, barres de progression)
- **API REST** avec FastAPI pour intégration complète

### 🔧 Fonctionnalités Avancées
- **Tests automatisés** avec pytest
- **Sauvegarde parallèle** de plusieurs VMs
- **Retention automatique** des anciennes sauvegardes
- **Scripts pré/post-sauvegarde** personnalisables
- **Métriques et monitoring** intégrés
- **Configuration flexible** via fichiers .env ou variables d'environnement

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

## 🚀 Démarrage Rapide

### 1️⃣ Lancement du Système Complet
```bash
# Démarrer l'interface web avec scheduler intégré
python3 kvm_monitor.py

# 🌐 Interface disponible : http://localhost:8080
# ⏰ Scheduler automatique : Activé
# 📊 Monitoring temps réel : Disponible
```

### 2️⃣ Première Sauvegarde via Interface Web
1. **Accédez à** http://localhost:8080
2. **Section "Machines Virtuelles"**
3. **Cliquez "💾 Sauvegarder"** sur une VM
4. **Suivez le progrès** dans "Tâches de sauvegarde"

### 3️⃣ Créer une Sauvegarde Programmée
1. **Section "Sauvegardes Programmées"**
2. **Bouton "➕ Nouvelle Planification"**
3. **Configurez** : nom, VMs, type (quotidien/hebdomadaire/mensuel), heure
4. **Sauvegarde automatique** selon la planification

### 4️⃣ Alternative CLI
```bash
# Sauvegarde immédiate
./main.py backup mainserver onlyoffice --mode incremental

# Planification via CLI
python3 schedule_manager.py add "Daily Backup" \
  --vms mainserver onlyoffice \
  --type daily --time "02:00" \
  --mode incremental
```

## 🎯 Utilisation Détaillée

### 🌐 Interface Web de Monitoring (Recommandée)

#### Démarrage
```bash
# Démarrer le serveur de monitoring
python3 kvm_monitor.py

# Accès à l'interface
# URL: http://localhost:8080
```

#### Fonctionnalités Web
- **Dashboard temps réel** : Statut système et VMs
- **Gestion des VMs** : Snapshots et sauvegardes en un clic
- **Sauvegardes programmées** : Interface complète de planification
- **Monitoring des tâches** : Suivi en temps réel des opérations
- **Actualisation automatique** : Données mises à jour automatiquement

### ⏰ Sauvegardes Programmées

#### Interface Web
1. Accédez à http://localhost:8080
2. Section "Sauvegardes Programmées"
3. Bouton "➕ Nouvelle Planification"
4. Configurez : nom, VMs, type, heure, mode

#### Gestionnaire CLI
```bash
# Lister les sauvegardes programmées
python3 schedule_manager.py list

# Créer une sauvegarde quotidienne
python3 schedule_manager.py add "Daily Backup" \
  --vms mainserver onlyoffice \
  --type daily --time "02:00" \
  --mode incremental

# Créer une sauvegarde hebdomadaire
python3 schedule_manager.py add "Weekly Full" \
  --vms mainserver onlyoffice \
  --type weekly --time "sunday:03:00" \
  --mode full

# Créer une sauvegarde mensuelle
python3 schedule_manager.py add "Monthly Snapshot" \
  --vms mainserver \
  --type monthly --time "1:04:00" \
  --mode snapshot

# Gérer les planifications
python3 schedule_manager.py enable <id>      # Activer
python3 schedule_manager.py disable <id>     # Désactiver
python3 schedule_manager.py remove <id>      # Supprimer

# Voir les sauvegardes dues
python3 schedule_manager.py due
```

### 💻 Interface en ligne de commande

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

### 🌐 Interface Web de Monitoring
```bash
# Démarrer l'interface de monitoring
python3 kvm_monitor.py

# Accès au dashboard : http://localhost:8080
```

**Fonctionnalités du dashboard :**
- 📊 Statut système en temps réel
- 💻 Liste des VMs avec états
- 📈 Tâches de sauvegarde en cours
- ⏰ Sauvegardes programmées avec prochaines exécutions
- 🔄 Actualisation automatique toutes les 30 secondes

### 📝 Logs Structurés
```bash
# Suivre les logs en temps réel
tail -f /var/log/kvm-backup/kvm-backup.log

# Filtrer par VM
grep '"vm_name":"vm1"' /var/log/kvm-backup/kvm-backup.log | jq .

# Filtrer par erreurs
grep '"level":"ERROR"' /var/log/kvm-backup/kvm-backup.log | jq .

# Logs du scheduler
grep '"logger":"kvm_backup.scheduler"' /var/log/kvm-backup/kvm-backup.log | jq .
```

### 🔍 Tests et Validation
```bash
# Tester le système de planification
python3 test_scheduler.py

# Tester une sauvegarde simple
./main.py backup vm1 --dry-run

# Vérifier la configuration
./main.py config
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

## ⏰ Automatisation Avancée

### 🎯 Scheduler Intégré (Recommandé)
Le système dispose d'un scheduler intégré qui remplace avantageusement cron :

```bash
# Démarrer le système avec scheduler automatique
python3 kvm_monitor.py

# Le scheduler vérifie automatiquement les planifications toutes les minutes
# Interface web : http://localhost:8080 pour gérer les planifications
```

**Avantages du scheduler intégré :**
- ✅ Interface web intuitive
- ✅ Gestion d'erreurs robuste avec reprogrammation
- ✅ Logs structurés et monitoring
- ✅ Configuration persistante
- ✅ Pas de configuration cron nécessaire

### 📅 Alternative Cron (Manuel)
Si vous préférez cron pour certaines tâches spécifiques :

```bash
# Éditer le crontab
sudo crontab -e

# Sauvegardes automatiques via CLI
# Incrémentielle quotidienne à 2h
0 2 * * * cd /home/authentik/backup-kvm/app_backup_kvm && ./main.py backup vm1 vm2 vm3 --mode incremental

# Complète hebdomadaire le dimanche à 1h  
0 1 * * 0 cd /home/authentik/backup-kvm/app_backup_kvm && ./main.py backup vm1 vm2 vm3 --mode full

# Nettoyage mensuel des anciens snapshots
0 3 1 * * cd /home/authentik/backup-kvm/app_backup_kvm && ./main.py cleanup-snapshots --older-than 30
```

### 🔄 Gestion des Planifications
```bash
# Via interface web (recommandé)
# http://localhost:8080 → Section "Sauvegardes Programmées"

# Via CLI
python3 schedule_manager.py list                    # Lister
python3 schedule_manager.py add "Name" --vms vm1    # Ajouter
python3 schedule_manager.py enable <id>             # Activer
python3 schedule_manager.py disable <id>            # Désactiver
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

## 🆚 Avantages vs Solutions Traditionnelles

| Fonctionnalité | Script Bash | Python App KVM Backup |
|---|---|---|
| **Snapshots sans arrêt VM** | ❌ | ✅ |
| **Interface web moderne** | ❌ | ✅ Dashboard complet |
| **Sauvegardes programmées** | ⚠️ Cron manuel | ✅ Scheduler intégré |
| **Monitoring temps réel** | ❌ | ✅ Interface web |
| **API REST** | ❌ | ✅ FastAPI |
| **Logs structurés** | ❌ | ✅ JSON + monitoring |
| **Tests automatisés** | ❌ | ✅ pytest |
| **Gestion d'erreurs** | ⚠️ Basic | ✅ Robuste + reprogrammation |
| **Configuration flexible** | ⚠️ Variables | ✅ .env + interface web |
| **Transfert SSH optimisé** | ⚠️ rsync simple | ✅ rsync + compression |
| **Interface planification** | ❌ | ✅ Web + CLI professionnel |
| **Persistance planning** | ❌ | ✅ JSON + backup auto |

### 🎯 Pourquoi Choisir Cette Solution

**🚀 Facilité d'utilisation :**
- Interface web intuitive pour tous les utilisateurs
- CLI riche pour les administrateurs avancés
- Configuration via interface ou fichiers

**⚡ Performance :**
- Snapshots sans downtime des VMs
- Transferts rsync optimisés avec compression
- Exécution parallèle possible

**🔒 Fiabilité :**
- Gestion d'erreurs complète avec reprogrammation automatique
- Logs structurés pour diagnostic facile
- Tests automatisés pour validation

**📈 Évolutivité :**
- API REST pour intégration dans d'autres systèmes
- Architecture modulaire facilement extensible
- Support de multiples serveurs de destination
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

## 🐛 Résolution de Problèmes

### 🔧 Erreurs Communes

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
ssh-add ~/.ssh/kvm-backup-key
```

**Interface web inaccessible :**
```bash
# Vérifier si le serveur fonctionne
ps aux | grep kvm_monitor

# Vérifier le port
netstat -tlnp | grep 8080

# Redémarrer le serveur
python3 kvm_monitor.py
```

**Sauvegardes programmées ne s'exécutent pas :**
```bash
# Vérifier le scheduler
python3 schedule_manager.py list

# Voir les sauvegardes dues
python3 schedule_manager.py due

# Vérifier les logs
tail -f /var/log/kvm-backup/kvm-backup.log | grep scheduler
```

### 📋 Tests de Validation
```bash
# Tester le système complet
python3 test_scheduler.py

# Tester une sauvegarde
./main.py backup vm1 --dry-run

# Vérifier la configuration
./main.py config
```
ssh-add -l
```

**Snapshots échouent :**
```bash
# Vérifier si la VM supporte les snapshots
virsh domblklist vm1
# Les disques doivent être en qcow2
```

## � Documentation Complète

- **📖 [Guide de Configuration](CONFIG_GUIDE.md)** - Configuration détaillée et exemples
- **🆕 [Nouvelles Fonctionnalités](NOUVELLES_FONCTIONNALITES.md)** - Sauvegardes programmées
- **📝 Logs** : `/var/log/kvm-backup/`
- **⚙️ Configuration** : `.env` dans le répertoire app
- **🧪 Tests** : `python3 test_scheduler.py` et `python -m pytest test_kvm_backup.py -v`

## 🌐 Interfaces Disponibles

- **Interface Web** : http://localhost:8080 (Dashboard principal)
- **API REST** : http://localhost:8000/docs (Documentation interactive)
- **CLI Backup** : `./main.py --help`
- **CLI Planification** : `python3 schedule_manager.py --help`

## 📞 Support et Maintenance

### Surveillance Système
```bash
# Vérifier le statut du service
ps aux | grep kvm_monitor

# Surveiller les logs en temps réel
tail -f /var/log/kvm-backup/kvm-backup.log

# Vérifier l'espace disque du serveur distant
python3 -c "from ssh_client import SSHClient; ssh = SSHClient('192.168.26.27', 'authentik', 'server'); ssh.connect(); print(ssh.get_disk_usage('/home/authentik/backup-kvm'))"
```

### Maintenance Planifiée
- **Nettoyage automatique** : Configuré via interface web
- **Rotation des logs** : Gestion automatique
- **Monitoring espace disque** : Intégré au dashboard
- **Tests réguliers** : Utiliser `python3 test_scheduler.py`

---

## 🏆 **Système KVM Backup Complet - Production Ready !**

**✅ Interface web moderne avec monitoring temps réel**  
**✅ Sauvegardes programmées automatiques**  
**✅ Transfert SSH sécurisé vers serveur distant**  
**✅ CLI professionnel pour administration**  
**✅ Architecture modulaire et extensible**

Cette solution moderne remplace complètement les scripts bash traditionnels avec une interface intuitive et des fonctionnalités de niveau entreprise.

**🚀 Prêt pour déploiement en production !**
