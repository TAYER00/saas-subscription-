from playwright.sync_api import sync_playwright
import os
import json
import pandas as pd
import re
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
            return 'Offres Online'
    
    def convert_date_to_standard_format(date_text):
        return date_text  # Fallback simple

class OffresonlineScraper:
    def __init__(self):
        self.data_dir = os.path.join('data', 'offresonline')
        os.makedirs(self.data_dir, exist_ok=True)
        
    def scrape(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                print("Navigation vers la page de connexion...")
                page.goto('https://offresonline.com/')
                
                print("Clic sur le bouton de connexion...")
                page.click('#main-nav > ul > li:nth-child(2) > a')
                
                print("Attente des champs de connexion...")
                page.wait_for_selector('#Login')
                page.wait_for_selector('#pwd')
                
                print("Remplissage des informations d'authentification...")
                page.fill('#Login', 'HYATT2')
                page.fill('#pwd', 'HYATTHALMI')
                
                print("Soumission du formulaire de connexion...")
                page.click('#buuuttt')
                
                print("Attente après connexion...")
                page.wait_for_timeout(10000)
                
                print("Navigation vers la page des appels d'offres...")
                page.goto('https://offresonline.com/Admin/alert.aspx?i=a&url=5')
                
                print("Attente du chargement du tableau des appels d'offres...")
                page.wait_for_selector('#tableao')
                
                tenders = []
                for i in range(1, 13):
                    print(f"Extraction de l'appel d'offres {i}...")
                    
                    # XPath pour chaque élément
                    objet_xpath = f"//table[@id='tableao']//tr[{i}]/td[2]"
                    date_xpath = f"//table[@id='tableao']//tr[{i}]/td[3]/b[1]"
                    
                    objet_elem = page.locator(f"xpath={objet_xpath}")
                    date_elem = page.locator(f"xpath={date_xpath}")
                    
                    if objet_elem.count() == 0:
                        print(f"Ligne {i} non trouvée, passage à la suivante.")
                        continue
                    
                    objet_text = objet_elem.text_content()
                    if not objet_text:
                        print(f"Objet vide à la ligne {i}, passage à la suivante.")
                        continue
                    
                    tender = {
                        'objet': objet_text.strip()
                    }
                    
                    if date_elem.count() > 0:
                        date_text = date_elem.text_content()
                        if date_text and date_text.strip():
                            formatted_date = convert_date_to_standard_format(date_text.strip())
                            tender['date_limite'] = formatted_date
                        else:
                            tender['date_limite'] = None
                    else:
                        tender['date_limite'] = None
                    
                    # Extraction du lien dans l'attribut onclick
                    onclick = objet_elem.get_attribute('onclick')
                    if onclick:
                        # Expression simple pour extraire l'URL entre apostrophes dans window.location='...'
                        match = re.search(r"window\.location\s*=\s*'([^']+)'", onclick)
                        if not match:
                            # Essayer aussi window.open('...')
                            match = re.search(r"window\.open\s*\(\s*'([^']+)'", onclick)
                        tender['link'] = match.group(1) if match else None
                    else:
                        tender['link'] = None
                    
                    print(f"Objet: {tender['objet'][:50]}..., Date limite: {tender['date_limite']}, Link: {tender['link']}")
                    tenders.append(tender)
                
                print(f"Extraction terminée. {len(tenders)} appels d'offres extraits.")

                # Filtrer les nouveaux appels d'offres (déduplication)
                print(f"Appels d'offres extraits avant déduplication: {len(tenders)}")
                site_name = DeduplicationService.get_site_name_from_scraper_class(self.__class__.__name__)
                new_tenders = DeduplicationService.filter_new_tenders(tenders, site_name)
                
                # Exporter les données (seulement les nouveaux)
                if new_tenders:
                    self._export_data(new_tenders)
                    print("Export des données terminé avec succès.")
                    return new_tenders  # Retourner seulement les nouveaux
                else:
                    print("Aucun nouvel appel d'offres trouvé.")
                    return []
                
            finally:
                browser.close()
    
    def _export_data(self, new_tenders):
        try:
            # Charger les données existantes et les fusionner
            existing_data = []
            json_path = os.path.join(self.data_dir, 'offresonline_tenders.json')
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
                json.dump(all_tenders, f, ensure_ascii=False, indent=4)
            print(f"Données exportées vers {json_path}")
            
            # Export to Excel (données complètes)
            print("Exportation vers Excel...")
            excel_path = os.path.join(self.data_dir, 'offresonline_tenders.xlsx')
            df = pd.DataFrame(all_tenders)
            df.to_excel(excel_path, index=False)
            print(f"Données exportées vers {excel_path}")
            
            print(f"Export terminé: {len(new_tenders)} nouveaux appels d'offres ajoutés.")
            print(f"Total des appels d'offres: {len(all_tenders)}")
            
            return True
        except Exception as e:
            print(f"Erreur lors de l'export des données: {str(e)}")
            return False

# Pour lancer le scraper
if __name__ == "__main__":
    scraper = OffresonlineScraper()
    scraper.scrape()
