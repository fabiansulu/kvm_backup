# 📋 Changelog - KVM Backup System

## 🎉 Version 2.0.0 - Sauvegardes Programmées (30 juillet 2025)

### ✨ Nouvelles Fonctionnalités Majeures

#### ⏰ Système de Planification Complet
- **Scheduler intégré** avec daemon automatique
- **Trois types de planification** : quotidien, hebdomadaire, mensuel
- **Interface web intuitive** pour créer et gérer les planifications
- **CLI professionnel** avec Rich UI pour administration avancée
- **Persistance automatique** dans `scheduled_backups.json`
- **Gestion d'erreurs robuste** avec reprogrammation automatique

#### 🌐 Interface Web Améliorée
- **Section "Sauvegardes Programmées"** avec monitoring temps réel
- **Modal de création interactive** avec sélection multiple de VMs
- **Statuts visuels** : activé/désactivé, prochaine exécution, historique
- **Actualisation automatique** toutes les minutes pour les planifications
- **Gestion complète** : activer, désactiver, supprimer directement

#### 🖥️ CLI de Gestion Avancé
- **Nouveau script `schedule_manager.py`** avec interface Rich
- **Commandes complètes** : `add`, `list`, `remove`, `enable`, `disable`, `due`
- **Tableaux colorés** pour affichage des planifications
- **Validation des données** et gestion d'erreurs

### 🔧 Améliorations Techniques

#### Architecture
- **Module `scheduler.py`** avec classe `BackupScheduler`
- **Intégration native** avec le `BackupManager` existant
- **Threading sécurisé** pour exécution en arrière-plan
- **Logs structurés** pour toutes les opérations de planification

#### API REST Étendue
- **Endpoints `/api/scheduled`** pour gestion des planifications
- **Support CRUD complet** : création, lecture, mise à jour, suppression
- **Validation JSON** des données de planification

#### Sécurité et Fiabilité
- **Démarrage automatique** du scheduler avec l'interface web
- **Reprogrammation intelligente** après échec ou succès
- **Logs détaillés** pour audit et diagnostic
- **Sauvegarde automatique** des configurations

### 📱 Interface Utilisateur

#### Types de Planification Supportés
```bash
# Quotidien à heure fixe
--type daily --time "02:00"

# Hebdomadaire avec jour + heure
--type weekly --time "sunday:03:00"

# Mensuel avec jour du mois + heure
--type monthly --time "15:04:00"
```

#### Modes de Sauvegarde
- **incremental** : Sauvegarde incrémentielle (défaut)
- **full** : Sauvegarde complète
- **snapshot** : Snapshot uniquement

### 🎯 Exemples d'Utilisation

#### Configuration Type Entreprise
```bash
# Sauvegarde quotidienne à 2h
python3 schedule_manager.py add "Daily Backup" \
  --vms mainserver onlyoffice \
  --type daily --time "02:00" \
  --mode incremental

# Sauvegarde hebdomadaire complète
python3 schedule_manager.py add "Weekly Full" \
  --vms mainserver onlyoffice \
  --type weekly --time "sunday:03:00" \
  --mode full
```

### 📊 Monitoring et Surveillance

#### Dashboard Web
- **Section dédiée** aux sauvegardes programmées
- **Indicateurs visuels** : statut, prochaine exécution
- **Historique** : dernière exécution réussie/échouée

#### Logs Structurés
- **Logger spécialisé** : `kvm_backup.scheduler`
- **Événements tracés** : création, exécution, erreurs
- **Format JSON** pour analyse automatisée

### 🔄 Migration et Compatibilité

#### Rétrocompatibilité
- ✅ **Toutes les fonctionnalités existantes** préservées
- ✅ **Interface CLI originale** (`main.py`) inchangée
- ✅ **Configuration existante** (.env) compatible
- ✅ **API REST existante** maintenue

#### Nouvelles Dépendances
- **Aucune dépendance externe** supplémentaire
- **Utilise les modules existants** : BackupManager, SSHClient
- **Threading standard Python** pour le scheduler

### 🧪 Tests et Validation

#### Script de Test
- **`test_scheduler.py`** pour validation complète
- **Tests des calculs** de prochaines exécutions
- **Tests CRUD** des planifications
- **Simulation** des sauvegardes dues

#### Validation CLI
- **Tests interactifs** via `schedule_manager.py`
- **Dry-run support** pour tests sans exécution
- **Validation des configurations** avant sauvegarde

### 📚 Documentation

#### Guides Mis à Jour
- **[README.md](README.md)** avec section sauvegardes programmées
- **[CONFIG_GUIDE.md](CONFIG_GUIDE.md)** avec exemples de planification
- **[QUICKSTART.md](QUICKSTART.md)** pour démarrage rapide
- **[NOUVELLES_FONCTIONNALITES.md](NOUVELLES_FONCTIONNALITES.md)** détaillé

#### Exemples Pratiques
- **Configurations type entreprise**
- **Scénarios d'utilisation courants**
- **Dépannage et diagnostics**

---

## 📋 Version 1.0.0 - Système de Base (Précédent)

### Fonctionnalités Initiales
- ✅ Sauvegardes KVM avec snapshots
- ✅ Transfert SSH vers serveur distant
- ✅ Interface web de monitoring
- ✅ CLI avec Typer et Rich
- ✅ API REST avec FastAPI
- ✅ Configuration flexible (.env)
- ✅ Logs structurés JSON

---

## 🎯 Prochaines Versions Prévues

### Version 2.1.0 (Planifiée)
- **Notifications** : Email/Slack pour échecs de sauvegarde
- **Métriques avancées** : Temps d'exécution, taille des backups
- **Interface mobile** responsive améliorée

### Version 2.2.0 (En réflexion)
- **Multi-serveurs** : Sauvegarde vers plusieurs destinations
- **Chiffrement** : Chiffrement des sauvegardes
- **Restauration guidée** : Interface web pour restauration

---

**🎉 Version 2.0.0 - Une évolution majeure vers un système de backup professionnel complet !**
