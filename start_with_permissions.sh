#!/bin/bash
# Script de démarrage avec les bonnes permissions pour KVM Backup

# S'assurer que l'utilisateur a les bonnes permissions
echo "Démarrage KVM Backup Monitor avec permissions libvirt..."

# Option 1: Utiliser sudo avec NOPASSWD pour l'application
exec sudo python3 kvm_monitor.py

# Option 2: Alternative - utiliser sg (si configuré)
# exec sg libvirt -c "python3 kvm_monitor.py"
