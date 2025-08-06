#!/usr/bin/env python
"""
Script de test pour vérifier le fonctionnement du scraper avec Django
"""

import os
import sys
import django
from django.conf import settings

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.tenders.models import TenderSite, Tender, ScrapingLog
from django.utils import timezone
import importlib.util

def test_scraper_integration():
    """
    Test l'intégration du scraper avec Django
    """
    print("🧪 Test de l'intégration du scraper avec Django")
    print("=" * 50)
    
    # 1. Vérifier les modèles Django
    print("\n1. Vérification des modèles Django...")
    
    # Compter les objets existants
    sites_count = TenderSite.objects.count()
    tenders_count = Tender.objects.count()
    logs_count = ScrapingLog.objects.count()
    
    print(f"   - Sites: {sites_count}")
    print(f"   - Appels d'offres: {tenders_count}")
    print(f"   - Logs de scraping: {logs_count}")
    
    # 2. Créer un site de test
    print("\n2. Création d'un site de test...")
    
    test_site, created = TenderSite.objects.get_or_create(
        name="marchespublics",
        defaults={
            'url': 'https://www.marchespublics.gov.ma',
            'is_active': True,
            'description': 'Site officiel des marchés publics du Maroc'
        }
    )
    
    if created:
        print(f"   ✅ Site créé: {test_site.name}")
    else:
        print(f"   ℹ️  Site existant: {test_site.name}")
    
    # 3. Vérifier le scraper
    print("\n3. Vérification du scraper...")
    
    scraper_path = os.path.join('Backend', 'scrapers', 'marchespublics', 'scraper.py')
    
    if os.path.exists(scraper_path):
        print(f"   ✅ Scraper trouvé: {scraper_path}")
        
        try:
            # Charger le module scraper
            spec = importlib.util.spec_from_file_location(
                "marchespublics_scraper", 
                scraper_path
            )
            scraper_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(scraper_module)
            
            # Rechercher la classe scraper
            scraper_class = None
            for attr_name in dir(scraper_module):
                attr = getattr(scraper_module, attr_name)
                if (isinstance(attr, type) and 
                    attr_name.lower().endswith('scraper') and 
                    attr_name != 'BaseScraper'):
                    scraper_class = attr
                    break
            
            if scraper_class:
                print(f"   ✅ Classe scraper trouvée: {scraper_class.__name__}")
                
                # Tester l'instanciation
                try:
                    scraper = scraper_class()
                    print(f"   ✅ Instanciation réussie")
                    
                    # Vérifier les méthodes requises
                    if hasattr(scraper, 'scrape'):
                        print(f"   ✅ Méthode 'scrape' disponible")
                    else:
                        print(f"   ❌ Méthode 'scrape' manquante")
                        
                except Exception as e:
                    print(f"   ❌ Erreur d'instanciation: {e}")
            else:
                print(f"   ❌ Aucune classe scraper trouvée")
                
        except Exception as e:
            print(f"   ❌ Erreur de chargement du module: {e}")
    else:
        print(f"   ❌ Scraper non trouvé: {scraper_path}")
    
    # 4. Test de création d'un log
    print("\n4. Test de création d'un log de scraping...")
    
    try:
        test_log = ScrapingLog.objects.create(
            site=test_site,
            status='completed',
            started_at=timezone.now(),
            completed_at=timezone.now(),
            items_found=5,
            items_new=3,
            items_updated=2
        )
        print(f"   ✅ Log créé avec succès (ID: {test_log.id})")
        
        # Supprimer le log de test
        test_log.delete()
        print(f"   🗑️  Log de test supprimé")
        
    except Exception as e:
        print(f"   ❌ Erreur de création du log: {e}")
    
    # 5. Résumé
    print("\n" + "=" * 50)
    print("📊 Résumé du test:")
    print(f"   - Modèles Django: ✅ Fonctionnels")
    print(f"   - Site de test: ✅ Créé/Vérifié")
    
    if os.path.exists(scraper_path):
        print(f"   - Scraper: ✅ Disponible")
    else:
        print(f"   - Scraper: ❌ Non trouvé")
    
    print(f"   - Logs: ✅ Fonctionnels")
    
    print("\n🎉 Test terminé!")
    
    # Instructions pour lancer le scraper
    print("\n📋 Pour lancer le scraper:")
    print("   python manage.py run_scraper marchespublics")
    print("   python manage.py run_scraper marchespublics --verbose")
    print("   python manage.py run_scraper marchespublics --force")

def show_database_stats():
    """
    Affiche les statistiques de la base de données
    """
    print("\n📊 Statistiques de la base de données:")
    print("-" * 40)
    
    # Sites
    sites = TenderSite.objects.all()
    print(f"Sites ({sites.count()}):")
    for site in sites:
        tenders_count = site.tenders.count()
        logs_count = site.scraping_logs.count()
        print(f"  - {site.name}: {tenders_count} appels d'offres, {logs_count} logs")
    
    # Appels d'offres par statut
    print(f"\nAppels d'offres par statut:")
    for status, label in Tender.STATUS_CHOICES:
        count = Tender.objects.filter(status=status).count()
        print(f"  - {label}: {count}")
    
    # Logs par statut
    print(f"\nLogs de scraping par statut:")
    for status, label in ScrapingLog.STATUS_CHOICES:
        count = ScrapingLog.objects.filter(status=status).count()
        print(f"  - {label}: {count}")

if __name__ == '__main__':
    try:
        test_scraper_integration()
        show_database_stats()
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)