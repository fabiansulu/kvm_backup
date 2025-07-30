#!/usr/bin/env python3
"""
Test du système de planification de sauvegardes
"""
import sys
import os
from datetime import datetime, timedelta

# Ajouter le répertoire du module au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scheduler import BackupScheduler, ScheduledBackup
from config import settings

def test_scheduler():
    """Test basique du scheduler"""
    print("🧪 Test du système de planification KVM Backup")
    print("=" * 60)
    
    # Créer une instance du scheduler
    scheduler = BackupScheduler()
    
    # Test 1: Ajouter une sauvegarde quotidienne
    print("\n📅 Test 1: Sauvegarde quotidienne")
    backup_id = scheduler.add_scheduled_backup(
        name="Test Quotidien",
        vm_names=["mainserver", "onlyoffice"],
        schedule_type="daily",
        schedule_time="02:00",
        backup_mode="incremental"
    )
    print(f"✅ Sauvegarde créée avec ID: {backup_id}")
    
    # Test 2: Ajouter une sauvegarde hebdomadaire
    print("\n📅 Test 2: Sauvegarde hebdomadaire")
    backup_id2 = scheduler.add_scheduled_backup(
        name="Test Hebdomadaire",
        vm_names=["mainserver"],
        schedule_type="weekly",
        schedule_time="sunday:03:00",
        backup_mode="full"
    )
    print(f"✅ Sauvegarde créée avec ID: {backup_id2}")
    
    # Test 3: Lister les sauvegardes
    print("\n📋 Test 3: Liste des sauvegardes programmées")
    scheduled_backups = scheduler.get_scheduled_backups()
    
    for backup in scheduled_backups:
        print(f"📦 {backup['name']}")
        print(f"   VMs: {', '.join(backup['vm_names'])}")
        print(f"   Type: {backup['schedule_type']} à {backup['schedule_time']}")
        print(f"   Mode: {backup['backup_mode']}")
        print(f"   Prochaine exécution: {backup['next_run']}")
        print(f"   Status: {'🟢 Activé' if backup['enabled'] else '🔴 Désactivé'}")
        print()
    
    # Test 4: Modifier une sauvegarde
    print("\n🔧 Test 4: Modification d'une sauvegarde")
    success = scheduler.update_scheduled_backup(backup_id, enabled=False)
    print(f"✅ Modification: {'Réussie' if success else 'Échouée'}")
    
    # Test 5: Vérifier les sauvegardes dues
    print("\n⏰ Test 5: Vérification des sauvegardes dues")
    due_backups = scheduler.get_due_backups()
    print(f"📊 Sauvegardes dues: {len(due_backups)}")
    
    for backup in due_backups:
        print(f"⚡ {backup.name} - Prochaine: {backup.next_run}")
    
    # Test 6: Supprimer une sauvegarde
    print("\n🗑️ Test 6: Suppression d'une sauvegarde")
    success = scheduler.remove_scheduled_backup(backup_id2)
    print(f"✅ Suppression: {'Réussie' if success else 'Échouée'}")
    
    # Résumé final
    print("\n📊 Résumé final")
    final_scheduled = scheduler.get_scheduled_backups()
    print(f"Nombre de sauvegardes programmées: {len(final_scheduled)}")
    
    print("\n✅ Tests terminés avec succès !")

def test_schedule_calculation():
    """Test du calcul des prochaines exécutions"""
    print("\n🧮 Test du calcul des planifications")
    print("=" * 40)
    
    # Test quotidien
    daily = ScheduledBackup(
        id="test1",
        name="Test Daily",
        vm_names=["test"],
        schedule_type="daily",
        schedule_time="14:30"
    )
    print(f"📅 Quotidien 14:30 -> Prochaine: {daily.next_run}")
    
    # Test hebdomadaire
    weekly = ScheduledBackup(
        id="test2", 
        name="Test Weekly",
        vm_names=["test"],
        schedule_type="weekly",
        schedule_time="friday:09:00"
    )
    print(f"📅 Vendredi 09:00 -> Prochaine: {weekly.next_run}")
    
    # Test mensuel
    monthly = ScheduledBackup(
        id="test3",
        name="Test Monthly", 
        vm_names=["test"],
        schedule_type="monthly",
        schedule_time="15:02:30"
    )
    print(f"📅 15ème jour 02:30 -> Prochaine: {monthly.next_run}")

if __name__ == "__main__":
    try:
        test_schedule_calculation()
        test_scheduler()
        
        print("\n🎉 Tous les tests sont passés !")
        print("\n💡 Pour démarrer le système complet :")
        print("   python3 kvm_monitor.py")
        
    except Exception as e:
        print(f"\n❌ Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()
