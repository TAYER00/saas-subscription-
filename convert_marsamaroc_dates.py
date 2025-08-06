#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour convertir les dates du fichier marsa_maroc_tenders.json
du format français vers un format compatible SQL (YYYY-MM-DD)
"""

import json
import re
from datetime import datetime

def convert_french_date_to_sql(french_date):
    """
    Convertit une date française (ex: "Ven 05 Sep 2025") vers le format SQL (YYYY-MM-DD)
    """
    # Mapping des mois français vers numéros
    french_months = {
        'Jan': '01', 'Fév': '02', 'Mar': '03', 'Avr': '04',
        'Mai': '05', 'Jun': '06', 'Jul': '07', 'Aoû': '08',
        'Sep': '09', 'Oct': '10', 'Nov': '11', 'Déc': '12'
    }
    
    try:
        # Extraire les composants de la date (ex: "Ven 05 Sep 2025")
        # Pattern: jour_semaine jour mois année
        pattern = r'\w+\s+(\d{1,2})\s+(\w+)\s+(\d{4})'
        match = re.match(pattern, french_date.strip())
        
        if not match:
            print(f"Format de date non reconnu: {french_date}")
            return None
            
        day, month_fr, year = match.groups()
        
        # Convertir le mois français en numéro
        month_num = french_months.get(month_fr)
        if not month_num:
            print(f"Mois non reconnu: {month_fr}")
            return None
            
        # Formater la date au format SQL (YYYY-MM-DD)
        sql_date = f"{year}-{month_num}-{day.zfill(2)}"
        
        # Valider la date
        datetime.strptime(sql_date, '%Y-%m-%d')
        
        return sql_date
        
    except Exception as e:
        print(f"Erreur lors de la conversion de '{french_date}': {e}")
        return None

def convert_marsamaroc_json():
    """
    Convertit toutes les dates du fichier marsa_maroc_tenders.json
    """
    input_file = 'data/marsamaroc/marsa_maroc_tenders.json'
    output_file = 'data/marsamaroc/marsa_maroc_tenders_converted.json'
    
    try:
        # Lire le fichier JSON
        with open(input_file, 'r', encoding='utf-8') as f:
            tenders = json.load(f)
        
        converted_count = 0
        error_count = 0
        
        # Convertir chaque date
        for tender in tenders:
            original_date = tender.get('date_limite', '')
            converted_date = convert_french_date_to_sql(original_date)
            
            if converted_date:
                tender['date_limite'] = converted_date
                tender['date_limite_original'] = original_date  # Garder l'original pour référence
                converted_count += 1
                print(f"✓ Converti: {original_date} → {converted_date}")
            else:
                error_count += 1
                print(f"✗ Erreur: {original_date}")
        
        # Sauvegarder le fichier converti
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(tenders, f, ensure_ascii=False, indent=2)
        
        print(f"\n=== RÉSUMÉ ===")
        print(f"Total des appels d'offres: {len(tenders)}")
        print(f"Dates converties avec succès: {converted_count}")
        print(f"Erreurs de conversion: {error_count}")
        print(f"Fichier de sortie: {output_file}")
        
        return True
        
    except FileNotFoundError:
        print(f"Erreur: Fichier {input_file} non trouvé")
        return False
    except json.JSONDecodeError:
        print(f"Erreur: Format JSON invalide dans {input_file}")
        return False
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return False

if __name__ == '__main__':
    print("=== CONVERSION DES DATES MARSA MAROC ===")
    print("Conversion du format français vers le format SQL (YYYY-MM-DD)\n")
    
    success = convert_marsamaroc_json()
    
    if success:
        print("\n✅ Conversion terminée avec succès!")
        print("Le fichier converti peut maintenant être importé en base de données.")
    else:
        print("\n❌ Échec de la conversion.")