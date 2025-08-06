from playwright.sync_api import sync_playwright
import pandas as pd
import json
import os
from datetime import datetime
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
            return 'Marchés Publics'

class MarchesPublicsScraper:
    def __init__(self):
        self.base_url = 'https://www.marchespublics.gov.ma/index.php?page=entreprise.EntrepriseHome'
        self.username = 'HYATTNEGOCE'
        self.password = 'HYATTHALMI2009'
        self.data_dir = 'data/marchespublics'
        os.makedirs(self.data_dir, exist_ok=True)

    def scrape(self):
        print("Démarrage du scraping de marchespublics.gov.ma...")
        try:
            with sync_playwright() as p:
                print("Lancement du navigateur...")
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Login
                print("Tentative de connexion...")
                page.goto(self.base_url)
                page.fill('#ctl0_CONTENU_PAGE_login', self.username)
                page.fill('#ctl0_CONTENU_PAGE_password', self.password)
                page.click('#ctl0_CONTENU_PAGE_authentificationButton')
                
                # Vérifier si la connexion a réussi
                error_message = page.query_selector('.error-message')
                if error_message:
                    raise Exception(f"Échec de connexion: {error_message.inner_text()}")
                print("Connexion réussie!")
                
                # Navigate to tender list
                print("Navigation vers la liste des appels d'offres...")
                try:
                    page.wait_for_selector('#menuAnnonces > li:nth-child(3) > a', timeout=5000)
                    page.click('#menuAnnonces > li:nth-child(3) > a')
                except Exception as e:
                    raise Exception("Menu des annonces non trouvé. Vérifiez si vous êtes bien connecté.")
                
                print("Lancement de la recherche...")
                page.click('#ctl0_CONTENU_PAGE_AdvancedSearch_lancerRecherche')
                
                # Extract data
                print("Extraction des données...")
                tenders = []
                table_selector = '#tabNav > div.ongletLayer > div.content > table'
                try:
                    page.wait_for_selector(table_selector, timeout=5000)
                    rows = page.query_selector_all(f"{table_selector} tr")
                    if not rows:
                        print("Tableau des résultats non trouvé ou vide")
                        return []
                except Exception as e:
                    print(f"Erreur lors de l'extraction du tableau: {str(e)}")
                    return []
                
                print(f"Nombre de lignes trouvées: {len(rows)-1}")
                for row in rows[1:]:  # Skip header row
                    tender = {}
                    
                    # Extract object
                    object_elem = row.query_selector('[id^="ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch_"][id$="_panelBlocObjet"]')
                    if object_elem:
                        tender['objet'] = object_elem.inner_text().strip()
                    
                    # Extract deadline date
                    deadline_elem = row.query_selector('#ctl0_CONTENU_PAGE_resultSearch_detailCons_ctl1_ctl0_dateHeureLimiteRemisePlis')
                    if deadline_elem:
                        tender['date_limite'] = deadline_elem.inner_text().strip()
                    else:
                        tender['date_limite'] = 'N/A'
                    
                    if tender and 'objet' in tender:
                        tenders.append(tender)
                
                browser.close()
                
                # Filtrer les nouveaux appels d'offres (déduplication)
                print(f"Appels d'offres extraits avant déduplication: {len(tenders)}")
                site_name = DeduplicationService.get_site_name_from_scraper_class(self.__class__.__name__)
                new_tenders = DeduplicationService.filter_new_tenders(tenders, site_name)
                
                # Export data (seulement les nouveaux)
                if new_tenders:
                    print(f"Exportation de {len(new_tenders)} nouveaux appels d'offres...")
                    self._export_data(new_tenders)
                    print("Scraping terminé avec succès!")
                    return new_tenders
                else:
                    print("Aucun nouvel appel d'offres trouvé.")
                    return []
                
        except Exception as e:
            print(f"\nERREUR lors du scraping: {str(e)}")
            return []
    
    def _export_data(self, new_tenders):
        try:
            # Export to text file (nouveaux seulement)
            print("Exportation vers fichier texte...")
            txt_path = f'{self.data_dir}/data.txt'
            with open(txt_path, 'w', encoding='utf-8') as f:
                for tender in new_tenders:
                    f.write(f"Objet: {tender.get('objet', 'N/A')}\n")
                    f.write(f"Date limite: {tender.get('date_limite', 'N/A')}\n")
                    f.write('---\n')
            print(f"Données exportées vers {txt_path}")
            
            # Charger les données existantes et les fusionner
            existing_data = []
            json_path = f'{self.data_dir}/marches_publics_tenders.json'
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
            excel_path = f'{self.data_dir}/marches_publics_tenders.xlsx'
            df = pd.DataFrame(all_tenders)
            df.to_excel(excel_path, index=False)
            print(f"Données exportées vers {excel_path}")
            
            print(f"Export terminé: {len(new_tenders)} nouveaux appels d'offres ajoutés.")
            print(f"Total des appels d'offres: {len(all_tenders)}")
            
        except Exception as e:
            print(f"Erreur lors de l'exportation des données: {str(e)}")