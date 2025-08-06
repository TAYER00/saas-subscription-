import os
import sys
import django
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.tenders.models import TenderSite, ScrapingLog
import importlib.util
import traceback

class Command(BaseCommand):
    help = 'Lance un scraper pour un site spécifique'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'site_name',
            type=str,
            help='Nom du site à scraper (ex: marchespublics)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force le scraping même si un autre est en cours'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Affichage détaillé des logs'
        )
    
    def handle(self, *args, **options):
        site_name = options['site_name']
        force = options['force']
        verbose = options['verbose']
        
        try:
            # Vérifier si le site existe dans la base de données
            try:
                site = TenderSite.objects.get(name=site_name)
            except TenderSite.DoesNotExist:
                # Créer le site s'il n'existe pas
                site = TenderSite.objects.create(
                    name=site_name,
                    url=f"https://{site_name}.com",  # URL par défaut
                    is_active=True
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Site "{site_name}" créé dans la base de données')
                )
            
            # Vérifier s'il y a déjà un scraping en cours
            if not force:
                running_logs = ScrapingLog.objects.filter(
                    site=site,
                    status='running'
                )
                if running_logs.exists():
                    raise CommandError(
                        f'Un scraping est déjà en cours pour {site_name}. '
                        'Utilisez --force pour forcer l\'exécution.'
                    )
            
            # Construire le chemin vers le scraper
            scraper_path = os.path.join(
                'Backend', 'scrapers', site_name, 'scraper.py'
            )
            
            if not os.path.exists(scraper_path):
                raise CommandError(
                    f'Scraper non trouvé: {scraper_path}\n'
                    f'Assurez-vous que le fichier existe dans Backend/scrapers/{site_name}/scraper.py'
                )
            
            # Créer un log de scraping
            log = ScrapingLog.objects.create(
                site=site,
                status='running',
                started_at=timezone.now()
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Démarrage du scraping pour {site_name}...')
            )
            
            try:
                # Charger dynamiquement le module scraper
                spec = importlib.util.spec_from_file_location(
                    f"{site_name}_scraper", 
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
                
                if not scraper_class:
                    raise CommandError(
                        f'Aucune classe scraper trouvée dans {scraper_path}\n'
                        'La classe doit se terminer par "Scraper"'
                    )
                
                # Instancier et lancer le scraper
                scraper = scraper_class()
                
                if verbose:
                    self.stdout.write('Lancement du scraping...')
                
                # Exécuter le scraping
                if hasattr(scraper, 'scrape'):
                    result = scraper.scrape()
                elif hasattr(scraper, 'run'):
                    result = scraper.run()
                else:
                    raise CommandError(
                        f'La classe {scraper_class.__name__} doit avoir une méthode "scrape" ou "run"'
                    )
                
                # Mettre à jour le log avec les résultats
                log.status = 'completed'
                log.completed_at = timezone.now()
                
                if isinstance(result, dict):
                    log.items_found = result.get('items_found', 0)
                    log.items_new = result.get('items_new', 0)
                    log.items_updated = result.get('items_updated', 0)
                elif isinstance(result, int):
                    log.items_found = result
                
                log.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Scraping terminé avec succès pour {site_name}\n'
                        f'Items trouvés: {log.items_found}\n'
                        f'Nouveaux items: {log.items_new}\n'
                        f'Items mis à jour: {log.items_updated}'
                    )
                )
                
            except Exception as e:
                # Mettre à jour le log avec l'erreur
                log.status = 'failed'
                log.completed_at = timezone.now()
                log.error_message = str(e)
                log.save()
                
                error_msg = f'Erreur lors du scraping de {site_name}: {str(e)}'
                if verbose:
                    error_msg += f'\n\nTraceback:\n{traceback.format_exc()}'
                
                raise CommandError(error_msg)
                
        except CommandError:
            raise
        except Exception as e:
            raise CommandError(f'Erreur inattendue: {str(e)}')
    
    def get_available_scrapers(self):
        """Retourne la liste des scrapers disponibles"""
        scrapers_dir = os.path.join('Backend', 'scrapers')
        available_scrapers = []
        
        if os.path.exists(scrapers_dir):
            for item in os.listdir(scrapers_dir):
                scraper_path = os.path.join(scrapers_dir, item, 'scraper.py')
                if os.path.isdir(os.path.join(scrapers_dir, item)) and os.path.exists(scraper_path):
                    available_scrapers.append(item)
        
        return available_scrapers