#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour exécuter tous les scrapers en parallèle
Auteur: Assistant IA
Date: 2025
"""

import os
import sys
import subprocess
import threading
import time
from datetime import datetime

# Ajouter le répertoire racine au path Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Liste des scrapers à exécuter
SCRAPERS = [
    "scrapers\\adm\\scraper.py",
    "scrapers\\cgi\\scraper.py", 
    "scrapers\\marchespublics\\scraper.py",
    "scrapers\\marsamaroc\\scraper.py",
    "scrapers\\offresonline\\scraper.py",
    "scrapers\\royalairmaroc\\scraper.py"
]

def run_scraper(scraper_path):
    """
    Exécute un scraper individuel
    """
    scraper_name = os.path.basename(os.path.dirname(scraper_path))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Démarrage du scraper: {scraper_name}")
    
    try:
        # Configurer l'environnement pour gérer l'encodage UTF-8
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # Exécuter le scraper
        result = subprocess.run(
            [sys.executable, scraper_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if result.returncode == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {scraper_name} terminé avec succès")
            if result.stdout:
                print(f"[{scraper_name}] Output: {result.stdout.strip()}")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ {scraper_name} a échoué")
            if result.stderr:
                print(f"[{scraper_name}] Erreur: {result.stderr.strip()}")
                
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Erreur lors de l'exécution de {scraper_name}: {str(e)}")

def main():
    """
    Fonction principale pour exécuter tous les scrapers
    """
    print("="*60)
    print("🚀 DÉMARRAGE DE TOUS LES SCRAPERS")
    print("="*60)
    print(f"Heure de début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Nombre de scrapers à exécuter: {len(SCRAPERS)}")
    print("="*60)
    
    # Vérifier que tous les fichiers scrapers existent
    missing_scrapers = []
    for scraper in SCRAPERS:
        if not os.path.exists(scraper):
            missing_scrapers.append(scraper)
    
    if missing_scrapers:
        print("⚠️  ATTENTION: Les scrapers suivants sont introuvables:")
        for scraper in missing_scrapers:
            print(f"   - {scraper}")
        print("")
    
    # Filtrer les scrapers existants
    existing_scrapers = [s for s in SCRAPERS if os.path.exists(s)]
    
    if not existing_scrapers:
        print("❌ Aucun scraper trouvé. Vérifiez les chemins.")
        return
    
    start_time = time.time()
    
    # Créer et démarrer les threads pour chaque scraper
    threads = []
    for scraper in existing_scrapers:
        thread = threading.Thread(target=run_scraper, args=(scraper,))
        threads.append(thread)
        thread.start()
        # Petit délai entre les démarrages pour éviter la surcharge
        time.sleep(0.5)
    
    # Attendre que tous les threads se terminent
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    duration = end_time - start_time
    
    print("="*60)
    print("🏁 TOUS LES SCRAPERS TERMINÉS")
    print("="*60)
    print(f"Heure de fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Durée totale: {duration:.2f} secondes")
    print(f"Scrapers exécutés: {len(existing_scrapers)}")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Interruption par l'utilisateur (Ctrl+C)")
        print("Arrêt en cours...")
    except Exception as e:
        print(f"❌ Erreur inattendue: {str(e)}")
        sys.exit(1)