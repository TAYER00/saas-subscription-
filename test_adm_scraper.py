#!/usr/bin/env python3
"""
Script de test pour le scraper ADM modifié
"""

import os
import sys
import django
from pathlib import Path

# Ajouter le répertoire du projet au PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from Backend.scrapers.adm.scraper import AdmScraper
import asyncio

async def test_adm_scraper():
    """
    Test du scraper ADM pour vérifier l'extraction des dates limites
    """
    print("🚀 Démarrage du test du scraper ADM...")
    
    scraper = AdmScraper()
    
    try:
        # Lancer le scraping
        result = await scraper.scrape()
        
        print(f"\n📊 Résultats du scraping:")
        print(f"Nombre d'appels d'offres trouvés: {len(result)}")
        
        # Afficher les premiers résultats avec focus sur les dates
        for i, tender in enumerate(result[:5]):
            print(f"\n--- Appel d'offres {i+1} ---")
            print(f"Objet: {tender.get('objet', 'N/A')[:100]}...")
            print(f"Date limite: {tender.get('date_limite', 'N/A')}")
            print(f"Lien: {tender.get('link', 'N/A')}")
        
        # Statistiques sur les dates
        dates_found = [t for t in result if t.get('date_limite') and t.get('date_limite') != 'N/A']
        print(f"\n📅 Statistiques des dates:")
        print(f"Dates limites trouvées: {len(dates_found)}/{len(result)}")
        print(f"Pourcentage de réussite: {(len(dates_found)/len(result)*100):.1f}%")
        
        if dates_found:
            print("\n✅ Exemples de dates trouvées:")
            for tender in dates_found[:3]:
                print(f"  - {tender.get('date_limite')} pour: {tender.get('objet', '')[:80]}...")
        
        return result
        
    except Exception as e:
        print(f"❌ Erreur lors du scraping: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    # Exécuter le test
    result = asyncio.run(test_adm_scraper())
    
    if result:
        print(f"\n🎉 Test terminé avec succès! {len(result)} appels d'offres extraits.")
    else:
        print("\n❌ Test échoué - aucun résultat obtenu.")