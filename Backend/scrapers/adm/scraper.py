from playwright.sync_api import sync_playwright
import os
import json
import pandas as pd
from datetime import datetime
import re
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
            return 'ADM'

class AdmScraper:
    def __init__(self):
        self.data_dir = os.path.join('data', 'adm')
        os.makedirs(self.data_dir, exist_ok=True)
        
    def scrape(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Accéder à la page de connexion
                print("Navigation vers la page de connexion...")
                page.goto('https://achats.adm.co.ma/?page=entreprise.EntrepriseHome&goto=')
                
                # Fermer le popup modal
                print("Fermeture du popup...")
                page.wait_for_selector('#modalADM > div > div > div.modal-footer > button')
                page.click('#modalADM > div > div > div.modal-footer > button')
                
                # Attendre que les champs de connexion soient visibles
                page.wait_for_selector('#ctl0_CONTENU_PAGE_login')
                page.wait_for_selector('#ctl0_CONTENU_PAGE_password')
                
                # Remplir les informations d'authentification
                print("Remplissage des informations d'authentification...")
                page.fill('#ctl0_CONTENU_PAGE_login', 'HYATTNEGOCESERVICE')
                page.fill('#ctl0_CONTENU_PAGE_password', 'HYATT159/*')
                
                # Prendre une capture d'écran avant la connexion
                page.screenshot(path=os.path.join(self.data_dir, 'before_login.png'))
                
                # Cliquer sur le bouton de connexion
                print("Soumission du formulaire de connexion...")
                page.click('#ctl0_CONTENU_PAGE_authentificationButton')
                
                # Attendre 10 secondes après la connexion
                page.wait_for_timeout(10000)
                
                # Prendre une capture d'écran après la connexion
                page.screenshot(path=os.path.join(self.data_dir, 'post_login.png'))
                
                # Naviguer directement vers la page des appels d'offres
                print("Navigation vers la page des appels d'offres...")
                page.goto('https://achats.adm.co.ma/?page=entreprise.EntrepriseAdvancedSearch&AllCons&searchAnnCons')
                
                # Attendre 10 secondes après la navigation
                page.wait_for_timeout(10000)
                
                # Prendre une capture d'écran après la navigation
                page.screenshot(path=os.path.join(self.data_dir, 'post_navigation.png'))
                
                # Attendre que le conteneur des appels d'offres soit visible
                print("Attente du chargement du conteneur des appels d'offres...")
                page.wait_for_selector('#tabNav > div.p-2 > div.content')
                
                # Prendre une capture d'écran avant l'extraction
                page.screenshot(path=os.path.join(self.data_dir, 'page_before_extraction.png'))
                
                # Extraire les données
                print("Extraction des données...")
                tenders = []
                seen_objects = set()  # Pour suivre les objets déjà vus
                tender_items = page.query_selector_all('div.contentColumn')
                
                # Scraper les liens pour les indices 2 à 7
                for index in range(2, 8):  # Modifié pour inclure jusqu'à l'index 7
                    try:
                        # Sélectionner l'élément de l'appel d'offres
                        item = page.query_selector(f'#tabNav > div.p-2 > div.content > div:nth-child({index})')
                        if not item:
                            print(f"Élément {index} non trouvé, passage au suivant")
                            continue

                        objet = item.query_selector('div.info.p-card div.p-objet')
                        date_limite = item.query_selector('div.leftColumn div.limita')
                        
                        # Extraire le lien avec le sélecteur incrémenté
                        link = 'N/A'
                        onclick = item.get_attribute('onclick')
                        print(f"DEBUG onclick pour l'élément {index}:", onclick)  # 🔍 à supprimer plus tard

                        if onclick:
                            match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", onclick)
                            if match:
                                link = match.group(1)

                        # Nettoyer et formater les données
                        objet_text = objet.text_content().strip() if objet else 'N/A'
                        
                        # Extraire la date limite
                        date_text = 'N/A'
                        if date_limite:
                            # Chercher d'abord dans le span
                            date_span = date_limite.query_selector('span')
                            if date_span:
                                date_text = date_span.text_content().strip()
                            # Si pas de span ou texte vide, prendre tout le contenu
                            if not date_text:
                                date_text = date_limite.text_content().strip()
                        
                        # Supprimer les labels redondants
                        objet_text = objet_text.replace('Objet\n                                                        : \n                                                    ', '')
                        date_text = date_text.replace('Date limite de remise des plis', '')
                        
                        # Nettoyer les textes
                        objet_text = objet_text.strip()
                        date_text = date_text.strip() if date_text.strip() else 'N/A'
                        
                        # Vérifier si cet objet a déjà été vu
                        if objet_text not in seen_objects:
                            seen_objects.add(objet_text)
                            tender = {
                                'objet': objet_text,
                                'date_limite': date_text,
                                'link': link
                            }
                            tenders.append(tender)
                    except Exception as e:
                        print(f"Erreur lors de l'extraction de l'appel d'offres {index} : {str(e)}")
                        continue
                
                # Filtrer les nouveaux appels d'offres (déduplication)
                print(f"Appels d'offres extraits avant déduplication: {len(tenders)}")
                site_name = DeduplicationService.get_site_name_from_scraper_class(self.__class__.__name__)
                new_tenders = DeduplicationService.filter_new_tenders(tenders, site_name)
                
                # Exporter les données (seulement les nouveaux)
                if new_tenders:
                    # Export en format texte
                    with open(os.path.join(self.data_dir, 'data.txt'), 'w', encoding='utf-8') as f:
                        for tender in new_tenders:
                            f.write(f"Objet: {tender['objet']}\n")
                            f.write(f"Date limite: {tender['date_limite']}\n")
                            f.write(f"Lien: {tender['link']}\n")
                            f.write("---\n")
                    
                    # Charger les données existantes et les fusionner
                    existing_data = []
                    json_file_path = os.path.join(self.data_dir, 'adm_tenders.json')
                    if os.path.exists(json_file_path):
                        try:
                            with open(json_file_path, 'r', encoding='utf-8') as f:
                                existing_data = json.load(f)
                        except (json.JSONDecodeError, FileNotFoundError):
                            existing_data = []
                    
                    # Fusionner les nouvelles données avec les existantes
                    all_tenders = existing_data + new_tenders
                    
                    # Export en JSON (données complètes)
                    with open(json_file_path, 'w', encoding='utf-8') as f:
                        json.dump(all_tenders, f, ensure_ascii=False, indent=2)
                    
                    # Export en Excel (données complètes)
                    df = pd.DataFrame(all_tenders)
                    df.to_excel(os.path.join(self.data_dir, 'adm_tenders.xlsx'), index=False)
                    
                    print(f"Extraction terminée. {len(new_tenders)} nouveaux appels d'offres ajoutés.")
                    print(f"Total des appels d'offres: {len(all_tenders)}")
                    
                    return new_tenders  # Return only new tenders
                else:
                    print("Aucun nouvel appel d'offres trouvé.")
                    return []
                    
            except Exception as e:
                print(f"Une erreur est survenue : {str(e)}")
                # Prendre une capture d'écran en cas d'erreur
                page.screenshot(path=os.path.join(self.data_dir, 'error.png'))
                raise
            
            finally:
                browser.close()

if __name__ == '__main__':
    scraper = AdmScraper()
    scraper.scrape()