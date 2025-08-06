from playwright.sync_api import sync_playwright
import pandas as pd
import json
import os
from datetime import datetime
import time
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import conditionnel pour éviter les erreurs Django
try:
    from scrapers.services import DeduplicationService
except ImportError:
    # Fallback pour usage autonome
    class DeduplicationService:
        @staticmethod
        def filter_new_tenders(tenders, site_name):
            return tenders
        
        @staticmethod
        def get_site_name_from_scraper_class(scraper_class):
            return 'Royal Air Maroc'

class RoyalAirMarocScraper:
    def __init__(self):
        self.base_url = 'https://ram-esourcing.royalairmaroc.com/web/login.html'
        self.username = 'assistantecom2@hyatt-negoce.com'
        self.password = 'HYATTHALMI200'
        self.data_dir = 'data/royalairmaroc'
        self.max_retries = 3
        self.retry_delay = 10  # secondes
        os.makedirs(self.data_dir, exist_ok=True)

    def scrape(self):
        print("Démarrage du scraping de ram-esourcing.royalairmaroc.com...")
        for attempt in range(self.max_retries):
            try:
                with sync_playwright() as p:
                    print(f"Tentative {attempt + 1}/{self.max_retries}")
                    print("Lancement du navigateur...")
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.set_default_timeout(180000)  # Augmenter le timeout à 180 secondes
                    
                    # Accéder à la page d'authentification
                    print("Accès à la page d'authentification...")
                    page.goto(self.base_url, wait_until='networkidle', timeout=180000)
                    
                    # Login
                    print("Tentative de connexion...")
                    page.fill('#username', self.username)
                    page.fill('#password', self.password)
                    page.click('#Entrer')
                    
                    # Attendre que la page se charge après la connexion
                    print("Attente de chargement après connexion...")
                    page.wait_for_load_state('networkidle', timeout=180000)
                    page.wait_for_load_state('domcontentloaded')
                    page.wait_for_timeout(20000)  # Augmenter l'attente à 20 secondes
                    
                    # Vérifier si la connexion a réussi
                    print("Vérification de la connexion...")
                    page.screenshot(path=os.path.join(self.data_dir, 'post_login.png'))
                    
                    # Cliquer sur le lien vers la page des appels d'offres
                    print("Navigation vers la liste des appels d'offres...")
                    try:
                        post_login_selector = '#dijit__WidgetsInTemplateMixin_3 > div > div.frameWidgetContent > div:nth-child(1) > div > table > tbody > tr:nth-child(3) > td:nth-child(2) > a'
                        page.wait_for_selector(post_login_selector, timeout=180000)
                        
                        # Vérifier si l'élément est visible et cliquable
                        element = page.query_selector(post_login_selector)
                        if not element or not element.is_visible():
                            print("Le lien des appels d'offres n'est pas visible")
                            page.screenshot(path=os.path.join(self.data_dir, 'link_not_visible.png'))
                            if attempt < self.max_retries - 1:
                                print(f"Nouvelle tentative dans {self.retry_delay} secondes...")
                                time.sleep(self.retry_delay)
                                continue
                            return []
                        
                        element.click()
                        
                        # Attendre que la page soit complètement chargée
                        print("Attente du chargement complet de la page...")
                        page.wait_for_load_state('networkidle', timeout=180000)
                        page.wait_for_load_state('domcontentloaded')
                        page.wait_for_timeout(20000)
                        page.screenshot(path=os.path.join(self.data_dir, 'post_navigation.png'))
                        
                    except Exception as e:
                        print(f"Erreur lors de la navigation: {str(e)}")
                        page.screenshot(path=os.path.join(self.data_dir, 'error.png'))
                        if attempt < self.max_retries - 1:
                            print(f"Nouvelle tentative dans {self.retry_delay} secondes...")
                            time.sleep(self.retry_delay)
                            continue
                        return []
                    
                    # Extract data
                    print("Extraction des données...")
                    tenders = []
                    
                    try:
                        # Attendre que le tableau soit visible
                        print("Recherche du tableau des appels d'offres...")
                        table_selector = '#chooseRfqFEBean > div > section > div.table-root > table'
                        page.wait_for_selector(table_selector, timeout=180000)
                        page.screenshot(path=os.path.join(self.data_dir, 'page_before_extraction.png'))
                        
                        # Extraire les données des appels d'offres
                        print("Extraction des appels d'offres...")
                        
                        # Boucler sur les indices de 1 à 20 pour extraire les appels d'offres
                        for index in range(1, 21):
                            try:
                                # Sélectionner la ligne de l'appel d'offres
                                row_selector = f'#chooseRfqFEBean > div > section > div.table-root > table > tbody.list-tbody.async-list-tbody > tr:nth-child({index})'
                                row = page.query_selector(row_selector)
                                
                                if not row:
                                    print(f"Ligne {index} non trouvée, passage à la suivante")
                                    continue
                                
                                tender = {}
                                
                                # Extraire l'objet
                                print(f"Extraction de l'objet pour la ligne {index}...")
                                object_elem = row.query_selector('td.col_TITLE.tdMedium')
                                if object_elem:
                                    tender['objet'] = object_elem.inner_text().strip()
                                    print(f"Objet trouvé: {tender['objet'][:50]}...")
                                
                                # Extraire la date limite
                                print(f"Extraction de la date limite pour la ligne {index}...")
                                date_elem = row.query_selector('td.col_INTEREST_TIME_LIMIT.tdMedium')
                                if date_elem:
                                    tender['date_limite'] = date_elem.inner_text().strip()
                                    print(f"Date limite trouvée: {tender['date_limite']}")
                                else:
                                    tender['date_limite'] = 'N/A'
                                
                                # Extraire le lien
                                print(f"Extraction du lien pour la ligne {index}...")
                                link_selector = f'td.col_TITLE.tdMedium > a'
                                link_elem = row.query_selector(link_selector)
                                if link_elem:
                                    href = link_elem.get_attribute('href')
                                    if href:
                                        # Nettoyer et formater le lien
                                        base_href = href.split('.do')[0] + '.do'
                                        # Supprimer 'init' du chemin
                                        cleaned_href = base_href.replace('/init', '/')
                                        tender['link'] = f"https://ram-esourcing.royalairmaroc.com{cleaned_href}"
                                        print(f"Lien trouvé pour la ligne {index}: {tender['link']}")
                                    else:
                                        tender['link'] = 'N/A'
                                        print(f"Pas de lien trouvé pour la ligne {index}")
                                else:
                                    tender['link'] = 'N/A'
                                    print(f"Élément lien non trouvé pour la ligne {index}")
                                
                                if tender and 'objet' in tender:
                                    tenders.append(tender)
                                    
                            except Exception as e:
                                print(f"Erreur lors de l'extraction de la ligne {index}: {str(e)}")
                                continue
                                
                    except Exception as e:
                        print(f"Erreur lors de l'extraction des données: {str(e)}")
                        page.screenshot(path=os.path.join(self.data_dir, 'extraction_error.png'))
                        if attempt < self.max_retries - 1:
                            print(f"Nouvelle tentative dans {self.retry_delay} secondes...")
                            time.sleep(self.retry_delay)
                            continue
                        return []
                    
                    print(f"Extraction terminée. {len(tenders)} appels d'offres extraits.")

                    # Filtrer les nouveaux appels d'offres (déduplication)
                    print(f"Appels d'offres extraits avant déduplication: {len(tenders)}")
                    site_name = DeduplicationService.get_site_name_from_scraper_class(self.__class__.__name__)
                    new_tenders = DeduplicationService.filter_new_tenders(tenders, site_name)
                    
                    # Exporter les données (seulement les nouveaux)
                    if new_tenders:
                        self._export_data(new_tenders)
                        print("Export des données terminé avec succès.")
                        print("Scraping de royalairmaroc terminé avec succès.")
                        return new_tenders  # Retourner seulement les nouveaux
                    else:
                        print("Aucun nouvel appel d'offres trouvé.")
                        print("Scraping de royalairmaroc terminé avec succès.")
                        return []
                    
            except Exception as e:
                print(f"Erreur lors du scraping: {str(e)}")
                if attempt < self.max_retries - 1:
                    print(f"Nouvelle tentative dans {self.retry_delay} secondes...")
                    time.sleep(self.retry_delay)
                    continue
                return []
    
    def _export_data(self, new_tenders):
        try:
            # Charger les données existantes et les fusionner
            existing_data = []
            json_path = os.path.join(self.data_dir, 'ram_esourcing_tenders.json')
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_data = []
            
            # Fusionner les nouvelles données avec les existantes
            all_tenders = existing_data + new_tenders
            
            # Export to JSON (données complètes)
            print("Exportation vers JSON...")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(all_tenders, f, ensure_ascii=False, indent=2)
            print(f"Données exportées vers {json_path}")
            
            # Export to Excel (données complètes)
            print("Exportation vers Excel...")
            excel_path = os.path.join(self.data_dir, 'ram_esourcing_tenders.xlsx')
            df = pd.DataFrame(all_tenders)
            df.to_excel(excel_path, index=False)
            print(f"Données exportées vers {excel_path}")
            
            print(f"Export terminé: {len(new_tenders)} nouveaux appels d'offres ajoutés.")
            print(f"Total des appels d'offres: {len(all_tenders)}")
            
            return True
        except Exception as e:
            print(f"Erreur lors de l'export des données: {str(e)}")
            return False

if __name__ == '__main__':
    scraper = RoyalAirMarocScraper()
    scraper.scrape()