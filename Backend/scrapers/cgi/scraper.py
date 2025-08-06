from playwright.sync_api import sync_playwright
import pandas as pd
import json
import os
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import conditionnel pour éviter les erreurs Django
try:
    from scrapers.services import DeduplicationService, convert_date_to_standard_format
except ImportError:
    # Fallback pour usage autonome
    class DeduplicationService:
        @staticmethod
        def filter_new_tenders(tenders, site_name):
            return tenders
        
        @staticmethod
        def get_site_name_from_scraper_class(scraper_class):
            return 'CGI E-Sourcing'
    
    def convert_date_to_standard_format(date_text):
        return date_text  # Fallback simple

class CGIESourcingScraper:
    def __init__(self):
        self.base_url = 'https://cgi-esourcing.app.jaggaer.com/web/index.html'
        self.username = 'HYATTNEGOCESERVICE'
        self.password = 'Paris2024!JeGagne'
        self.data_dir = 'data/cgi'
        os.makedirs(self.data_dir, exist_ok=True)

    def scrape(self):
        print("Démarrage du scraping de cgi-maroc.supplier.ariba.com...")
        tenders = []
        try:
            with sync_playwright() as p:
                print("Lancement du navigateur...")
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Accéder à la page d'authentification avec un délai plus long
                print("Accès à la page d'authentification...")
                page.set_default_timeout(60000)  # Augmenter le timeout à 60 secondes
                
                # Accéder à la page et attendre son chargement
                response = page.goto(self.base_url)
                print(f"Status de la réponse: {response.status if response else 'Pas de réponse'}")
                
                # Capture d'écran avant le chargement complet
                page.screenshot(path=f'{self.data_dir}/before_load.png')
                print("Capture d'écran avant le chargement sauvegardée")
                
                page.wait_for_load_state('networkidle', timeout=60000)
                print("État 'networkidle' atteint")
                
                # Capture d'écran après le chargement
                page.screenshot(path=f'{self.data_dir}/after_load.png')
                print("Capture d'écran après le chargement sauvegardée")
                
                # Login
                print("Tentative de connexion...")
                
                # Sauvegarder le HTML pour déboguer
                html_content = page.content()
                with open(f'{self.data_dir}/page_before_login.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print("HTML avant login sauvegardé")
                
                # Attendre et remplir le nom d'utilisateur
                try:
                    username_selector = page.wait_for_selector('#username', timeout=10000)
                    if username_selector:
                        username_selector.fill(self.username)
                        print("Nom d'utilisateur rempli")
                        page.screenshot(path=f'{self.data_dir}/after_username.png')
                    else:
                        print("Champ username non trouvé")
                except Exception as e:
                    print(f"Erreur lors du remplissage du nom d'utilisateur: {str(e)}")
                
                # Attendre et remplir le mot de passe
                try:
                    password_selector = page.wait_for_selector('#password', timeout=10000)
                    if password_selector:
                        password_selector.fill(self.password)
                        print("Mot de passe rempli")
                        page.screenshot(path=f'{self.data_dir}/after_password.png')
                    else:
                        print("Champ password non trouvé")
                except Exception as e:
                    print(f"Erreur lors du remplissage du mot de passe: {str(e)}")
                
                # Cliquer sur le bouton de connexion
                try:
                    submit_button = page.wait_for_selector('#navbarResponsive1 > ul > li > form > fieldset > div:nth-child(3) > input.btn.float-right', timeout=10000)
                    if submit_button:
                        submit_button.click()
                        print("Bouton de connexion cliqué")
                    else:
                        print("Bouton de connexion non trouvé")
                except Exception as e:
                    print(f"Erreur lors du clic sur le bouton de connexion: {str(e)}")
                
                try:
                    # Attendre le chargement complet après le clic
                    print("Attente du chargement complet après connexion...")
                    
                    # Attendre d'abord que la page commence à charger
                    page.wait_for_load_state('domcontentloaded', timeout=60000)
                    print("État 'domcontentloaded' atteint")
                    
                    # Sauvegarder le HTML pour déboguer l'état après connexion
                    with open(f'{self.data_dir}/page_after_login.html', 'w', encoding='utf-8') as f:
                        f.write(page.content())
                    print("HTML après connexion sauvegardé")
                    
                    # Attendre que toutes les requêtes réseau soient terminées
                    page.wait_for_load_state('networkidle', timeout=60000)
                    print("État 'networkidle' atteint")
                    
                    # Navigation vers la page des appels d'offres
                    print("Navigation vers la liste des appels d'offres...")
                    page.click('text=Appels d\'offres')
                    page.wait_for_load_state('networkidle', timeout=30000)
                    
                    # Capture d'écran après navigation vers la liste des appels d'offres
                    page.screenshot(path=f'{self.data_dir}/tenders_list.png')
                    print("Capture d'écran de la liste des appels d'offres sauvegardée")
                    
                    # Vérifier s'il y a des appels d'offres
                    print("Vérification de la présence d'appels d'offres...")
                    warning_message = page.query_selector('#OpportunityListManager > div > div.Alert-root.list-message.Alert-warning > div.Alert-message > span')
                    
                    if warning_message:
                        print("Aucun appel d'offre disponible.")
                        return []
                    
                    # Extraction des données
                    print("Extraction des données...")
                    tenders = []
                    tender_elements = page.query_selector_all('table.tender-list tr')
                    
                    for element in tender_elements[1:]:
                        tender = {}
                        tender['objet'] = element.query_selector('td:nth-child(2)').inner_text().strip()
                        
                        # Extraire et convertir la date
                        date_text = element.query_selector('td:nth-child(4)').inner_text().strip()
                        formatted_date = convert_date_to_standard_format(date_text)
                        tender['date_limite'] = formatted_date
                        
                        tenders.append(tender)
                    
                    # Filtrer les nouveaux appels d'offres (déduplication)
                    print(f"Appels d'offres extraits avant déduplication: {len(tenders)}")
                    site_name = DeduplicationService.get_site_name_from_scraper_class(self.__class__.__name__)
                    new_tenders = DeduplicationService.filter_new_tenders(tenders, site_name)
                    
                    # Export des données (seulement les nouveaux)
                    if new_tenders:
                        print(f"Exportation de {len(new_tenders)} nouveaux appels d'offres...")
                        self._export_data(new_tenders)
                        return new_tenders
                    else:
                        print("Aucun nouvel appel d'offres trouvé.")
                        return []
                    
                except Exception as e:
                    print(f"Erreur lors du scraping: {str(e)}")
                    if not page.is_closed():
                        page.screenshot(path=f'{self.data_dir}/error_state.png')
                    return []
        except Exception as e:
            print(f"Erreur globale lors du scraping: {str(e)}")
            return []
                
    def _export_data(self, new_tenders):
        try:
            # Export to text file (nouveaux seulement)
            print("Exportation vers fichier texte...")
            txt_path = f'{self.data_dir}/data.txt'
            with open(txt_path, 'w', encoding='utf-8') as f:
                for tender in new_tenders:
                    f.write(f"Objet: {tender.get('objet', 'N/A')}\n")
                    f.write(f"Date Limite: {tender.get('date_limite', 'N/A')}\n")
                    f.write('---\n')
            print(f"Données exportées vers {txt_path}")
            
            # Charger les données existantes et les fusionner
            existing_data = []
            json_path = f'{self.data_dir}/cgi_esourcing_tenders.json'
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
            excel_path = f'{self.data_dir}/cgi_esourcing_tenders.xlsx'
            df = pd.DataFrame(all_tenders)
            df.to_excel(excel_path, index=False)
            print(f"Données exportées vers {excel_path}")
            
            print(f"Export terminé: {len(new_tenders)} nouveaux appels d'offres ajoutés.")
            print(f"Total des appels d'offres: {len(all_tenders)}")
            
        except Exception as e:
            print(f"Erreur lors de l'exportation des données: {str(e)}")