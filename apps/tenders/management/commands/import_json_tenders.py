import json
import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.tenders.models import Tender, TenderSite
import hashlib
from datetime import datetime


class Command(BaseCommand):
    help = 'Importe tous les fichiers JSON du dossier data dans la base de données'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default='data',
            help='Répertoire contenant les fichiers JSON (défaut: data)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui serait importé sans modifier la base de données'
        )

    def handle(self, *args, **options):
        data_dir = options['data_dir']
        dry_run = options['dry_run']
        
        if not os.path.exists(data_dir):
            self.stdout.write(
                self.style.ERROR(f'Le répertoire {data_dir} n\'existe pas')
            )
            return

        # Mapping des dossiers vers les sites web
        site_mapping = {
            'adm': 'ADM - Autoroutes du Maroc',
            'marchespublics': 'Marchés Publics',
            'marsamaroc': 'Marsa Maroc',
            'offresonline': 'Offres Online',
            'royalairmaroc': 'Royal Air Maroc'
        }

        total_imported = 0
        total_updated = 0
        total_skipped = 0

        for site_folder in os.listdir(data_dir):
            site_path = os.path.join(data_dir, site_folder)
            
            if not os.path.isdir(site_path):
                continue
                
            site_name = site_mapping.get(site_folder, site_folder.title())
            
            self.stdout.write(
                self.style.SUCCESS(f'\nTraitement du site: {site_name}')
            )
            
            # Créer ou récupérer le site
            if not dry_run:
                site, created = TenderSite.objects.get_or_create(
                    name=site_name,
                    defaults={
                        'url': f'https://{site_folder}.com',  # URL par défaut
                        'description': f'Site d\'appels d\'offres {site_name}',
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(f'  Site créé: {site_name}')
            else:
                site = None
                self.stdout.write(f'  [DRY RUN] Site: {site_name}')
            
            # Traiter tous les fichiers JSON dans le dossier
            for filename in os.listdir(site_path):
                if not filename.endswith('.json'):
                    continue
                    
                file_path = os.path.join(site_path, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        tenders_data = json.load(f)
                    
                    self.stdout.write(f'  Fichier: {filename} ({len(tenders_data)} appels d\'offres)')
                    
                    for tender_data in tenders_data:
                        result = self.process_tender(tender_data, site, dry_run)
                        if result == 'imported':
                            total_imported += 1
                        elif result == 'updated':
                            total_updated += 1
                        else:
                            total_skipped += 1
                            
                except json.JSONDecodeError as e:
                    self.stdout.write(
                        self.style.ERROR(f'  Erreur JSON dans {filename}: {e}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  Erreur lors du traitement de {filename}: {e}')
                    )

        # Résumé
        self.stdout.write(
            self.style.SUCCESS(f'\n=== RÉSUMÉ ===')
        )
        if dry_run:
            self.stdout.write('Mode DRY RUN - Aucune modification en base')
        self.stdout.write(f'Appels d\'offres importés: {total_imported}')
        self.stdout.write(f'Appels d\'offres mis à jour: {total_updated}')
        self.stdout.write(f'Appels d\'offres ignorés: {total_skipped}')
        self.stdout.write(f'Total traité: {total_imported + total_updated + total_skipped}')

    def process_tender(self, tender_data, site, dry_run):
        """
        Traite un appel d'offres individuel
        """
        # Extraire les données
        objet = tender_data.get('objet', '') or ''
        date_limite = tender_data.get('date_limite', '') or ''
        link = tender_data.get('link', '') or ''
        
        # S'assurer que ce sont des chaînes
        objet = str(objet).strip()
        date_limite = str(date_limite).strip()
        link = str(link).strip() if link != 'None' else ''
        
        if not objet:
            return 'skipped'
        
        # Nettoyer l'objet (supprimer "Objet : " au début)
        if objet.startswith('Objet : '):
            objet = objet[8:].strip()
        elif objet.startswith('Objet: '):
            objet = objet[7:].strip()
        
        # Créer un hash unique pour détecter les doublons
        content_for_hash = f"{objet}_{link}_{site.name if site else 'unknown'}"
        content_hash = hashlib.sha256(content_for_hash.encode('utf-8')).hexdigest()
        
        if dry_run:
            self.stdout.write(f'    [DRY RUN] {objet[:100]}...')
            return 'imported'
        
        # Vérifier si l'appel d'offres existe déjà
        existing_tender = Tender.objects.filter(content_hash=content_hash).first()
        
        if existing_tender:
            return 'skipped'
        
        # Traiter la date limite
        deadline_date = None
        if date_limite and date_limite != 'N/A':
            try:
                # Essayer différents formats de date
                for date_format in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                    try:
                        deadline_date = datetime.strptime(date_limite, date_format)
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        
        # Créer l'appel d'offres
        try:
            tender = Tender.objects.create(
                title=objet,
                description=objet,  # Utiliser l'objet comme description par défaut
                site=site,
                source_url=link if link else '',
                deadline_date=deadline_date,
                content_hash=content_hash,
                status='open',  # Statut par défaut
                category='other',  # Catégorie par défaut
                scraped_at=timezone.now()
            )
            
            self.stdout.write(f'    ✓ Importé: {objet[:100]}...')
            return 'imported'
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'    ✗ Erreur lors de la création: {e}')
            )
            return 'skipped'