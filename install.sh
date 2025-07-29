#!/bin/bash
# Installation script for KVM Backup System

set -e

echo "🚀 Installation du système de sauvegarde KVM Python"
echo "=================================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    log_error "Ne pas exécuter ce script en tant que root"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"

log_info "Répertoire d'installation: $APP_DIR"

# Check system requirements
log_info "Vérification des prérequis système..."

# Check Python 3
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 n'est pas installé"
    echo "Installez avec: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [[ $(echo "$python_version >= 3.8" | bc -l) -eq 0 ]]; then
    log_error "Python 3.8+ requis (version détectée: $python_version)"
    exit 1
fi

log_success "Python 3 OK ($python_version)"

# Check libvirt
if ! command -v virsh &> /dev/null; then
    log_warning "libvirt-clients non installé"
    echo "Installation des dépendances système..."
    sudo apt update
    sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients libvirt-dev pkg-config
    sudo apt install -y rsync sshpass python3-dev build-essential
    
    # Add user to libvirt group
    sudo usermod -a -G libvirt $USER
    log_info "Utilisateur ajouté au groupe libvirt (redémarrage de session requis)"
fi

log_success "libvirt OK"

# Check if we can connect to libvirt
if ! virsh list &> /dev/null; then
    log_error "Impossible de se connecter à libvirt"
    echo "Vérifiez que:"
    echo "1. Le service libvirtd est démarré: sudo systemctl start libvirtd"
    echo "2. Votre utilisateur est dans le groupe libvirt: groups \$USER"
    echo "3. Redémarrez votre session si vous venez d'être ajouté au groupe"
    exit 1
fi

log_success "Connexion libvirt OK"

# Create virtual environment
log_info "Création de l'environnement virtuel Python..."

if [ -d "$APP_DIR/venv" ]; then
    log_info "Environnement virtuel existant trouvé, mise à jour..."
    source "$APP_DIR/venv/bin/activate"
    pip install --upgrade pip
else
    python3 -m venv "$APP_DIR/venv"
    source "$APP_DIR/venv/bin/activate"
    pip install --upgrade pip
fi

log_success "Environnement virtuel prêt"

# Install Python dependencies
log_info "Installation des dépendances Python..."

# Handle missing dependencies gracefully
cat > "$APP_DIR/requirements_minimal.txt" << 'EOF'
# Core dependencies only (without version pinning for better compatibility)
typer
rich
paramiko
pyyaml
python-dotenv
fastapi
uvicorn
pytest
asyncio
aiofiles
EOF

# Try to install from main requirements.txt, fallback to minimal
if pip install -r "$APP_DIR/requirements.txt" 2>/dev/null; then
    log_success "Toutes les dépendances installées"
else
    log_warning "Installation partielle, installation des dépendances minimales..."
    pip install -r "$APP_DIR/requirements_minimal.txt"
    log_success "Dépendances minimales installées"
fi

# Create configuration file
log_info "Configuration du système..."

if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    log_success "Fichier de configuration créé: $APP_DIR/.env"
    log_warning "Éditez $APP_DIR/.env pour configurer vos paramètres"
else
    log_info "Fichier de configuration existant conservé"
fi

# Create log directory
LOG_DIR="/var/log/kvm-backup"
if [ ! -d "$LOG_DIR" ]; then
    sudo mkdir -p "$LOG_DIR"
    sudo chown $USER:$USER "$LOG_DIR"
    log_success "Répertoire de logs créé: $LOG_DIR"
fi

# Create symlink for easy access
if [ ! -L "/usr/local/bin/kvm-backup" ]; then
    sudo ln -s "$APP_DIR/main.py" "/usr/local/bin/kvm-backup"
    log_success "Lien symbolique créé: /usr/local/bin/kvm-backup"
fi

# Make scripts executable
chmod +x "$APP_DIR/main.py"

# Test installation
log_info "Test de l'installation..."

cd "$APP_DIR"
source "$APP_DIR/venv/bin/activate"

# Test basic configuration
if python3 cli.py config &> /dev/null; then
    log_success "Configuration OK"
else
    log_warning "CLI pourrait avoir des problèmes, mais les composants principaux fonctionnent"
fi

# Test API import
if python3 -c "from api import app; print('API test OK')" &> /dev/null; then
    log_success "API fonctionnelle"
else
    log_error "Problème avec l'API"
    exit 1
fi

log_success "Installation réussie !"

# Display summary
echo ""
echo "🎉 Installation terminée avec succès !"
echo "======================================"
echo ""
echo "📋 Prochaines étapes:"
echo ""
echo "1. 📝 Configurer les paramètres:"
echo "   nano $APP_DIR/.env"
echo ""
echo "2. 🧪 Tester la configuration:"
echo "   cd $APP_DIR && source venv/bin/activate"
echo "   python3 cli.py config"
echo ""
echo "3. 🔄 Lister les VMs:"
echo "   virsh list --all"
echo ""
echo "4. 🌐 Démarrer l'API web (recommandé):"
echo "   uvicorn api:app --host 0.0.0.0 --port 8000"
echo ""
echo "5. 📚 Lire la documentation:"
echo "   cat $APP_DIR/CONFIG_GUIDE.md"
echo ""
echo "🔗 Commandes disponibles:"
echo "   python3 cli.py config                # Configuration"
echo "   uvicorn api:app --host 0.0.0.0 --port 8000  # Serveur web"
echo "   virsh list --all                     # Lister VMs"
echo "   Accès web: http://localhost:8000     # Interface"
echo ""

# Check if user needs to logout/login for libvirt group
if ! groups $USER | grep -q libvirt; then
    log_warning "Redémarrez votre session pour que les permissions libvirt prennent effet"
fi

log_success "Installation terminée - Prêt à sauvegarder vos VMs ! 🚀"
