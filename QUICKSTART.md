# 🚀 Guide de Démarrage Rapide - KVM Backup System

## ⚡ Mise en Service en 5 Minutes

### 1️⃣ **Démarrage Instantané**
```bash
cd /home/authentik/backup-kvm/app_backup_kvm

# Lancer le système complet
python3 kvm_monitor.py
```

**🌐 Interface Web :** http://localhost:8080  
**⏰ Scheduler :** Automatiquement activé  
**📊 Monitoring :** Temps réel  

### 2️⃣ **Première Sauvegarde (Interface Web)**

1. **Ouvrir** http://localhost:8080
2. **Section "Machines Virtuelles"**
3. **Cliquer "💾 Sauvegarder"** sur une VM
4. **Observer** le progrès dans "Tâches de sauvegarde"

### 3️⃣ **Planifier des Sauvegardes Automatiques**

#### Via Interface Web (Recommandé)
1. **Section "Sauvegardes Programmées"**
2. **"➕ Nouvelle Planification"**
3. **Configurer :**
   - Nom : "Sauvegarde Quotidienne"
   - VMs : Sélectionner mainserver, onlyoffice
   - Type : Quotidien
   - Heure : 02:00
   - Mode : Incrémentiel

#### Via CLI (Avancé)
```bash
# Sauvegarde quotidienne à 2h du matin
python3 schedule_manager.py add "Daily Backup" \
  --vms mainserver onlyoffice \
  --type daily --time "02:00" \
  --mode incremental

# Sauvegarde complète hebdomadaire le dimanche à 3h
python3 schedule_manager.py add "Weekly Full" \
  --vms mainserver onlyoffice \
  --type weekly --time "sunday:03:00" \
  --mode full
```

### 4️⃣ **Vérification du Système**

```bash
# Lister les planifications
python3 schedule_manager.py list

# Voir les sauvegardes dues
python3 schedule_manager.py due

# Tester le système
python3 test_scheduler.py
```

## 🎯 **Configuration Typique Entreprise**

### Planification Recommandée

```bash
# 1. Sauvegarde incrémentielle quotidienne (2h du matin)
python3 schedule_manager.py add "Daily Incremental" \
  --vms mainserver onlyoffice \
  --type daily --time "02:00" \
  --mode incremental

# 2. Sauvegarde complète hebdomadaire (dimanche 3h)
python3 schedule_manager.py add "Weekly Full Backup" \
  --vms mainserver onlyoffice \
  --type weekly --time "sunday:03:00" \
  --mode full

# 3. Snapshot mensuel (1er du mois à 4h)
python3 schedule_manager.py add "Monthly Snapshot" \
  --vms mainserver onlyoffice \
  --type monthly --time "1:04:00" \
  --mode snapshot
```

### Configuration SSH (Si pas déjà fait)

```bash
# Vérifier la connexion au serveur de sauvegarde
ssh authentik@192.168.26.27

# Créer le répertoire de destination
ssh authentik@192.168.26.27 "mkdir -p /home/authentik/backup-kvm/{configs,images}"
```

## 📊 **Surveillance et Monitoring**

### Dashboard Web
- **URL :** http://localhost:8080
- **Actualisation :** Automatique (30 secondes)
- **Sections :**
  - 📊 Statut système
  - 💻 Liste des VMs
  - 📈 Tâches en cours
  - ⏰ Sauvegardes programmées

### Logs en Temps Réel
```bash
# Suivre tous les logs
tail -f /var/log/kvm-backup/kvm-backup.log

# Logs du scheduler uniquement
tail -f /var/log/kvm-backup/kvm-backup.log | grep scheduler
```

## ⚠️ **Points d'Attention**

### Configuration Serveur Distant
Assurez-vous que le serveur 192.168.26.27 :
- ✅ Accepte les connexions SSH de l'utilisateur `authentik`
- ✅ A suffisamment d'espace disque
- ✅ Le répertoire `/home/authentik/backup-kvm` existe

### VMs Compatibles
- ✅ Disques en format qcow2 (pour les snapshots)
- ✅ Libvirt accessible depuis l'utilisateur courant

### Performance
- ⚡ Sauvegardes sans arrêt des VMs (via snapshots)
- ⚡ Transfert optimisé avec compression rsync
- ⚡ Exécution en arrière-plan

## 🎉 **Félicitations !**

Votre système KVM Backup est maintenant opérationnel avec :
- ✅ Interface web moderne
- ✅ Sauvegardes programmées automatiques
- ✅ Monitoring temps réel
- ✅ Transfert sécurisé vers serveur distant

**🌐 Accédez à votre dashboard :** http://localhost:8080

---

*Pour la documentation complète, consultez [README.md](README.md) et [CONFIG_GUIDE.md](CONFIG_GUIDE.md)*
