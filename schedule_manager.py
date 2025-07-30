#!/usr/bin/env python3
"""
Gestionnaire CLI pour les sauvegardes programmées KVM
"""
import argparse
import sys
import os
from datetime import datetime
from typing import List

# Ajouter le répertoire du module au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scheduler import BackupScheduler
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

console = Console()

def list_scheduled_backups(scheduler: BackupScheduler):
    """Afficher la liste des sauvegardes programmées"""
    scheduled_backups = scheduler.get_scheduled_backups()
    
    if not scheduled_backups:
        console.print("📋 Aucune sauvegarde programmée", style="yellow")
        return
    
    table = Table(title="⏰ Sauvegardes Programmées")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Nom", style="green")
    table.add_column("VMs", style="blue")
    table.add_column("Type", style="magenta")
    table.add_column("Heure", style="yellow")
    table.add_column("Mode", style="red")
    table.add_column("Status", style="white")
    table.add_column("Prochaine exécution", style="bright_green")
    
    for backup in scheduled_backups:
        next_run = datetime.fromisoformat(backup['next_run']).strftime('%d/%m/%Y %H:%M') if backup['next_run'] else 'N/A'
        status = "🟢 Activé" if backup['enabled'] else "🔴 Désactivé"
        
        table.add_row(
            backup['id'][:8],
            backup['name'],
            ', '.join(backup['vm_names']),
            backup['schedule_type'],
            backup['schedule_time'],
            backup['backup_mode'],
            status,
            next_run
        )
    
    console.print(table)

def add_scheduled_backup(scheduler: BackupScheduler, args):
    """Ajouter une nouvelle sauvegarde programmée"""
    try:
        backup_id = scheduler.add_scheduled_backup(
            name=args.name,
            vm_names=args.vms,
            schedule_type=args.type,
            schedule_time=args.time,
            backup_mode=args.mode
        )
        
        console.print(f"✅ Sauvegarde programmée créée avec succès !", style="green")
        console.print(f"📋 ID: {backup_id}", style="cyan")
        
        # Afficher les détails
        scheduled = scheduler.scheduled_backups[backup_id]
        console.print(Panel(
            f"[bold]Nom:[/bold] {scheduled.name}\n"
            f"[bold]VMs:[/bold] {', '.join(scheduled.vm_names)}\n"
            f"[bold]Type:[/bold] {scheduled.schedule_type}\n"
            f"[bold]Heure:[/bold] {scheduled.schedule_time}\n"
            f"[bold]Mode:[/bold] {scheduled.backup_mode}\n"
            f"[bold]Prochaine exécution:[/bold] {scheduled.next_run.strftime('%d/%m/%Y %H:%M')}",
            title="📦 Détails de la sauvegarde"
        ))
        
    except Exception as e:
        console.print(f"❌ Erreur lors de la création: {e}", style="red")

def remove_scheduled_backup(scheduler: BackupScheduler, backup_id: str):
    """Supprimer une sauvegarde programmée"""
    success = scheduler.remove_scheduled_backup(backup_id)
    
    if success:
        console.print(f"✅ Sauvegarde {backup_id[:8]} supprimée avec succès", style="green")
    else:
        console.print(f"❌ Sauvegarde {backup_id} introuvable", style="red")

def toggle_scheduled_backup(scheduler: BackupScheduler, backup_id: str, enabled: bool):
    """Activer/désactiver une sauvegarde programmée"""
    success = scheduler.update_scheduled_backup(backup_id, enabled=enabled)
    
    if success:
        status = "activée" if enabled else "désactivée"
        console.print(f"✅ Sauvegarde {backup_id[:8]} {status}", style="green")
    else:
        console.print(f"❌ Sauvegarde {backup_id} introuvable", style="red")

def show_due_backups(scheduler: BackupScheduler):
    """Afficher les sauvegardes dues"""
    due_backups = scheduler.get_due_backups()
    
    if not due_backups:
        console.print("📋 Aucune sauvegarde due actuellement", style="yellow")
        return
    
    table = Table(title="⚡ Sauvegardes Dues")
    table.add_column("Nom", style="green")
    table.add_column("VMs", style="blue")
    table.add_column("Mode", style="red")
    table.add_column("Prévue pour", style="yellow")
    
    for backup in due_backups:
        table.add_row(
            backup.name,
            ', '.join(backup.vm_names),
            backup.backup_mode,
            backup.next_run.strftime('%d/%m/%Y %H:%M')
        )
    
    console.print(table)

def main():
    parser = argparse.ArgumentParser(description="Gestionnaire de sauvegardes programmées KVM")
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')
    
    # Commande list
    list_parser = subparsers.add_parser('list', help='Lister les sauvegardes programmées')
    
    # Commande add
    add_parser = subparsers.add_parser('add', help='Ajouter une sauvegarde programmée')
    add_parser.add_argument('name', help='Nom de la sauvegarde')
    add_parser.add_argument('--vms', nargs='+', required=True, help='Liste des VMs à sauvegarder')
    add_parser.add_argument('--type', choices=['daily', 'weekly', 'monthly'], required=True, help='Type de planification')
    add_parser.add_argument('--time', required=True, help='Heure d\'exécution (ex: "02:00", "sunday:03:00", "15:04:00")')
    add_parser.add_argument('--mode', choices=['incremental', 'full', 'snapshot'], default='incremental', help='Mode de sauvegarde')
    
    # Commande remove
    remove_parser = subparsers.add_parser('remove', help='Supprimer une sauvegarde programmée')
    remove_parser.add_argument('id', help='ID de la sauvegarde à supprimer')
    
    # Commande enable/disable
    enable_parser = subparsers.add_parser('enable', help='Activer une sauvegarde programmée')
    enable_parser.add_argument('id', help='ID de la sauvegarde à activer')
    
    disable_parser = subparsers.add_parser('disable', help='Désactiver une sauvegarde programmée')
    disable_parser.add_argument('id', help='ID de la sauvegarde à désactiver')
    
    # Commande due
    due_parser = subparsers.add_parser('due', help='Afficher les sauvegardes dues')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialiser le scheduler
    scheduler = BackupScheduler()
    
    try:
        if args.command == 'list':
            list_scheduled_backups(scheduler)
        
        elif args.command == 'add':
            add_scheduled_backup(scheduler, args)
        
        elif args.command == 'remove':
            remove_scheduled_backup(scheduler, args.id)
        
        elif args.command == 'enable':
            toggle_scheduled_backup(scheduler, args.id, True)
        
        elif args.command == 'disable':
            toggle_scheduled_backup(scheduler, args.id, False)
        
        elif args.command == 'due':
            show_due_backups(scheduler)
    
    except KeyboardInterrupt:
        console.print("\n👋 Opération annulée", style="yellow")
    except Exception as e:
        console.print(f"❌ Erreur: {e}", style="red")

if __name__ == "__main__":
    main()
