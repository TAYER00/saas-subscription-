#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Services de déduplication pour les scrapers
"""

import os
import sys
import threading
from functools import wraps
import re
from datetime import datetime

def setup_django():
    """Configure Django si ce n'est pas déjà fait"""
    global DJANGO_AVAILABLE
    
    if DJANGO_AVAILABLE is not None:
        return DJANGO_AVAILABLE
    
    try:
        # Ajout du répertoire parent au path pour permettre l'import des modules Django
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # Configuration Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
        
        import django
        from django.conf import settings
        
        if not settings.configured:
            django.setup()
        
        DJANGO_AVAILABLE = True
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la configuration Django: {e}")
        DJANGO_AVAILABLE = False
        return False

# Initialisation globale
DJANGO_AVAILABLE = None
setup_django()

def convert_date_to_standard_format(date_text):
    """
    Convertit une date en texte vers le format standard YYYY-MM-DD
    
    Args:
        date_text (str): Texte contenant une date dans différents formats
        
    Returns:
        str: Date au format YYYY-MM-DD ou None si conversion impossible
    """
    if not date_text or date_text.strip() in ['N/A', '', 'Non spécifiée']:
        return None
    
    # Nettoyer le texte
    date_text = date_text.strip()
    
    # Patterns de dates courantes
    patterns = [
        # Format DD/MM/YYYY
        (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%d/%m/%Y'),
        # Format DD-MM-YYYY
        (r'(\d{1,2})-(\d{1,2})-(\d{4})', '%d-%m-%Y'),
        # Format DD.MM.YYYY
        (r'(\d{1,2})\.(\d{1,2})\.(\d{4})', '%d.%m.%Y'),
        # Format YYYY-MM-DD (déjà standard)
        (r'(\d{4})-(\d{1,2})-(\d{1,2})', '%Y-%m-%d'),
        # Format DD/MM/YY
        (r'(\d{1,2})/(\d{1,2})/(\d{2})', '%d/%m/%y'),
        # Format français avec jour: Jour DD Mois YYYY (ex: Mer 27 Aoû 2025)
        (r'\w+\s+(\d{1,2})\s+(jan|fév|mar|avr|mai|jun|jul|aoû|sep|oct|nov|déc|janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})', None),
        # Format français: DD mois YYYY
        (r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})', None),
        # Format anglais: Month DD, YYYY
        (r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})', None),
    ]
    
    # Dictionnaire pour les mois français (complets et abrégés)
    french_months = {
        'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
        'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
        'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12',
        'jan': '01', 'fév': '02', 'mar': '03', 'avr': '04',
        'mai': '05', 'jun': '06', 'jul': '07', 'aoû': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'déc': '12'
    }
    
    # Dictionnaire pour les mois anglais
    english_months = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12'
    }
    
    for pattern, date_format in patterns:
        match = re.search(pattern, date_text.lower())
        if match:
            try:
                if date_format:
                    # Format standard avec strptime
                    date_obj = datetime.strptime(match.group(0), date_format)
                    return date_obj.strftime('%Y-%m-%d')
                else:
                    # Traitement spécial pour les formats avec noms de mois
                    groups = match.groups()
                    if len(groups) == 3:
                        # Format avec jour de semaine: Jour DD Mois YYYY ou DD Mois YYYY
                        if any(month in date_text.lower() for month in french_months.keys()):
                            # Format français
                            day, month_name, year = groups
                            month = french_months.get(month_name.lower())
                            if month:
                                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        elif any(month in date_text.lower() for month in english_months.keys()):
                            # Format anglais
                            month_name, day, year = groups
                            month = english_months.get(month_name.lower())
                            if month:
                                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            except ValueError:
                continue
    
    # Si aucun pattern ne correspond, essayer d'extraire des nombres
    numbers = re.findall(r'\d+', date_text)
    if len(numbers) >= 3:
        try:
            # Supposer DD/MM/YYYY si les nombres sont dans cet ordre
            day, month, year = numbers[:3]
            if len(year) == 2:
                year = '20' + year if int(year) < 50 else '19' + year
            
            # Valider les valeurs
            if 1 <= int(day) <= 31 and 1 <= int(month) <= 12 and 1900 <= int(year) <= 2100:
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        except (ValueError, IndexError):
            pass
    
    return None

def run_in_thread(func):
    """Décorateur pour exécuter une fonction dans un thread séparé"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.start()
        thread.join()
        
        if exception[0]:
            raise exception[0]
        return result[0]
    return wrapper


class DeduplicationService:
    """
    Service de déduplication des appels d'offres
    """
    
    @staticmethod
    def get_site_name_from_scraper_class(scraper_class_name):
        """
        Retourne le nom du site basé sur le nom de la classe du scraper
        """
        mapping = {
            'AdmScraper': 'ADM - Autoroutes du Maroc',
            'MarchesPublicsScraper': 'Marchés Publics',
            'MarsaMarocScraper': 'Marsa Maroc',
            'OffresonlineScraper': 'Offres Online',
            'RoyalAirMarocScraper': 'Royal Air Maroc',
            'CGIESourcingScraper': 'CGI E-Sourcing'
        }
        return mapping.get(scraper_class_name, scraper_class_name)
    
    @staticmethod
    @run_in_thread
    def _filter_new_tenders_db(tenders, site_name):
        """Fonction interne pour la déduplication en base de données"""
        # S'assurer que Django est configuré
        if not setup_django():
            return tenders
        
        from apps.tenders.models import Tender, TenderSite
        from django.db import connection
        
        # Utiliser une requête SQL directe pour éviter les problèmes async
        with connection.cursor() as cursor:
            # Récupérer l'ID du site
            cursor.execute(
                "SELECT id FROM tenders_tendersite WHERE name = %s",
                [site_name]
            )
            site_result = cursor.fetchone()
            
            if not site_result:
                print(f"⚠️ Site '{site_name}' non trouvé en base - Tous les tenders seront considérés comme nouveaux")
                return tenders
            
            site_id = site_result[0]
            
            new_tenders = []
            existing_count = 0
            
            for tender_data in tenders:
                # Vérifier si l'appel d'offres existe déjà
                title = tender_data.get('objet', '').strip()
                
                if not title:
                    continue
                
                # Recherche par titre et site avec SQL direct
                cursor.execute(
                    "SELECT COUNT(*) FROM tenders_tender WHERE LOWER(title) = LOWER(%s) AND site_id = %s",
                    [title, site_id]
                )
                count = cursor.fetchone()[0]
                
                if count == 0:
                    new_tenders.append(tender_data)
                else:
                    existing_count += 1
            
            print(f"📊 Déduplication terminée:")
            print(f"   - Total extraits: {len(tenders)}")
            print(f"   - Déjà existants: {existing_count}")
            print(f"   - Nouveaux: {len(new_tenders)}")
            
            return new_tenders
    
    @staticmethod
    def filter_new_tenders(tenders, site_name):
        """
        Filtre les appels d'offres pour ne retourner que les nouveaux
        """
        if not DJANGO_AVAILABLE:
            print("⚠️ Django non disponible - Aucune déduplication effectuée")
            return tenders
        
        try:
            return DeduplicationService._filter_new_tenders_db(tenders, site_name)
        except Exception as e:
            print(f"❌ Erreur lors de la déduplication: {e}")
            print("⚠️ Retour de tous les tenders sans déduplication")
            return tenders
    
    @staticmethod
    def save_tenders_to_db(tenders, site_name):
        """
        Sauvegarde les appels d'offres en base de données
        """
        if not setup_django():
            print("⚠️ Django non disponible - Impossible de sauvegarder en base")
            return False
        
        try:
            from apps.tenders.models import Tender, TenderSite
            
            # Récupérer ou créer le site
            site, created = TenderSite.objects.get_or_create(
                name=site_name,
                defaults={'url': f'https://{site_name.lower().replace(" ", "")}.com'}
            )
            
            if created:
                print(f"✅ Site '{site_name}' créé en base")
            
            saved_count = 0
            
            for tender_data in tenders:
                title = tender_data.get('objet', '').strip()
                
                if not title:
                    continue
                
                # Créer l'appel d'offres
                tender, created = Tender.objects.get_or_create(
                    title=title,
                    site=site,
                    defaults={
                        'description': tender_data.get('description', ''),
                        'reference': tender_data.get('reference', ''),
                        'source_url': tender_data.get('link', ''),
                        'status': 'active'
                    }
                )
                
                if created:
                    saved_count += 1
            
            print(f"💾 {saved_count} nouveaux appels d'offres sauvegardés en base")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde: {e}")
            return False