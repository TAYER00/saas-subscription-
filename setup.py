#!/usr/bin/env python
"""
Script de configuration rapide pour SaaS Subscription Platform

Ce script automatise l'installation et la configuration initiale du projet.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_command(command, description=""):
    """Exécute une commande et affiche le résultat."""
    if description:
        print(f"\n🔄 {description}...")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ {description or 'Commande'} réussie")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de {description or 'la commande'}: {e}")
        if e.stdout:
            print(f"Sortie: {e.stdout}")
        if e.stderr:
            print(f"Erreur: {e.stderr}")
        return None


def check_python_version():
    """Vérifie la version de Python."""
    print("🔍 Vérification de la version Python...")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ est requis")
        sys.exit(1)
    
    print(f"✅ Python {sys.version.split()[0]} détecté")


def check_virtual_env():
    """Vérifie si un environnement virtuel est activé."""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Environnement virtuel détecté")
        return True
    else:
        print("⚠️  Aucun environnement virtuel détecté")
        response = input("Voulez-vous continuer sans environnement virtuel ? (y/N): ")
        return response.lower() == 'y'


def install_dependencies():
    """Installe les dépendances Python."""
    if not Path('requirements.txt').exists():
        print("❌ Fichier requirements.txt non trouvé")
        return False
    
    return run_command(
        "pip install -r requirements.txt",
        "Installation des dépendances"
    ) is not None


def setup_environment():
    """Configure le fichier d'environnement."""
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if env_file.exists():
        print("✅ Fichier .env déjà existant")
        return True
    
    if env_example.exists():
        try:
            shutil.copy(env_example, env_file)
            print("✅ Fichier .env créé à partir de .env.example")
            print("⚠️  N'oubliez pas de modifier les valeurs dans .env")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la création du fichier .env: {e}")
            return False
    else:
        print("❌ Fichier .env.example non trouvé")
        return False


def run_migrations():
    """Exécute les migrations Django."""
    commands = [
        ("python manage.py makemigrations", "Création des migrations"),
        ("python manage.py migrate", "Application des migrations")
    ]
    
    for command, description in commands:
        if run_command(command, description) is None:
            return False
    
    return True


def initialize_data():
    """Initialise les données de base."""
    return run_command(
        "python manage.py init_roles",
        "Initialisation des rôles et permissions"
    ) is not None


def collect_static():
    """Collecte les fichiers statiques."""
    return run_command(
        "python manage.py collectstatic --noinput",
        "Collecte des fichiers statiques"
    ) is not None


def create_superuser():
    """Propose de créer un superutilisateur."""
    response = input("\nVoulez-vous créer un superutilisateur ? (y/N): ")
    if response.lower() == 'y':
        return run_command(
            "python manage.py createsuperuser",
            "Création du superutilisateur"
        ) is not None
    return True


def display_success_message():
    """Affiche le message de succès."""
    print("""
🎉 Configuration terminée avec succès !

📋 Comptes de test disponibles :
   👤 Admin: admin@saas.com / admin123
   👤 Client: client@test.com / client123

🚀 Pour démarrer le serveur :
   python manage.py runserver

🌐 L'application sera accessible à :
   http://127.0.0.1:8000

📚 Consultez le README.md pour plus d'informations.
""")


def main():
    """Fonction principale du script de configuration."""
    print("""
🚀 Configuration de SaaS Subscription Platform
============================================
""")
    
    # Vérifications préliminaires
    check_python_version()
    
    if not check_virtual_env():
        print("❌ Configuration annulée")
        sys.exit(1)
    
    # Installation et configuration
    steps = [
        (install_dependencies, "Installation des dépendances"),
        (setup_environment, "Configuration de l'environnement"),
        (run_migrations, "Migrations de base de données"),
        (initialize_data, "Initialisation des données"),
        (collect_static, "Collecte des fichiers statiques"),
    ]
    
    for step_func, step_name in steps:
        print(f"\n📋 {step_name}")
        if not step_func():
            print(f"❌ Échec lors de: {step_name}")
            sys.exit(1)
    
    # Étapes optionnelles
    create_superuser()
    
    # Message de succès
    display_success_message()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Configuration interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        sys.exit(1)