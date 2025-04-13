import pandas as pd
import os
import re

# === PARAMÈTRES ===
FICHIER_SOLDES = "soldes_par_feuille.xlsx"
FICHIER_SORTIE = "Rapports_Financiers.xlsx"

# === CATEGORIES : PRÉFIXES OU INTERVALLES ===
CATEGORIES_BILAN = {
    'Liquidités': ['100','101','102','103','104','105'],
    'Avoirs à court terme cotés en bourse': ['106'],
    'Créances résultant de la vente': ['110','111','112','113'],
    'Autres créances à court terme': ['114','115','116','117','118','119'],
    'Stocks et travaux en cours': ['12'],
    'Actifs de régularisation': ['13'],
    'Immobilisations financières': ['14'],
    'Immobilisations corporelles meubles': ['15'],
    'Actifs immobilisés corporels immeubles': ['16'],
    'Immobilisations incorporelles': ['17'],
    'Capital non versé : capital social, capital de fondation': ['18'],
    'Attente': ['19'],
    'Dettes à court terme résultant d/’achats et de prestations de services': ['200', '201', '202', '203', '204', '205', '206', '207', '208','209'],
    'Dettes à court terme rémunérés': ['210', '211', '212', '213', '214', '215', '216', '217', '218','219'],
    'Autres dettes à court terme': ['220', '221', '222', '223', '224', '225', '226'],
    'Autres dettes à court terme (charges sociales)': ['227', '228','229'],
    'Passifs de régularisation et provisions à court terme': ['23'],
    'Dettes à long terme rémunérées': ['24'],
    'Autres dettes à long terme': ['25'],
    'Provisions à long terme et provisions légales': ['26'],
    'Dettes hors exploitation': ['27'],
    'Capital social ou capital de fondation': ['28'],
    'Réserves / bénéfices et pertes': ['29']
}

CATEGORIES_RESULTAT = {
    'Chiffre d’affaire résultant des ventes et des prestations de service': ['3'],
    'Charges de matériel, de marchandises et de prestations de tiers': ['4'],
    'Charges salarialesl': ['520','521','522','523','524','525','526'],
    'Charges sociales': ['527','5280'],
    'Autres charges de personnel': ['5281','5282','5283','5284','5285','5286','5287','5288','5289'],
    'Charges de tiers': ['529'],
    'Charges de locaux': ['60'],
    'Entretien, réparations, remplacement (ERR)': ['61'],
    'Charges de véhicules et de transport': ['62'],
    'Assurances-choses, droits, taxes': ['63'],
    'Charges d’énergie et évacuation': ['64'],
    'Charges d’administration et d’infrastructure': ['65'],
    'Charges de publicité': ['66'],
    'Autres charges d’exploitation': ['67'],
    'Amortissements et corrections de valeurs': ['68'],
    'Charges et produits financiers': ['69'],

    'Résultat des activités annexes d’exploitation': ['7'],
    'Résultats extraordinaires et hors exploitation': ['80','81','82','83','84','85','86','87','88'],
    'Impôts directs': ['89'],
    'Clôture et régularisations': ['9']
}

# === FONCTIONS ===

def charger_donnees():
    """Charge et nettoie les données comptables"""
    # Assurez-vous que extraction_gl a été exécuté et a généré le fichier
    if not os.path.exists(FICHIER_SOLDES):
        print(f"Erreur: Le fichier '{FICHIER_SOLDES}' n'existe pas.  Assurez-vous que extraction_gl.py a été exécuté en premier.")
        return None
    
    df = pd.read_excel(FICHIER_SOLDES)
    df['Compte'] = df['Compte'].astype(str).str.strip()
    df['Total Débit'] = pd.to_numeric(df['Total Débit'], errors='coerce').fillna(0)
    df['Total Crédit'] = pd.to_numeric(df['Total Crédit'], errors='coerce').fillna(0)
    df['Mouvement'] = df['Total Débit'] - df['Total Crédit']
    
    # Recherche dynamique de la colonne "Solde au..."
    solde_colonne = next((col for col in df.columns if re.match(r'Solde au', col, re.IGNORECASE)), None)
    if solde_colonne:
        df['Solde'] = pd.to_numeric(df[solde_colonne], errors='coerce').fillna(0)
    else:
        print("Avertissement : Colonne 'Solde au...' non trouvée. Utilisation d'une colonne par défaut ou arrêt du programme.")
        df['Solde'] = 0  # Ou une autre valeur par défaut, ou bien arrêter le programme
        
    return df

def appartient_a(compte: str, filtres) -> bool:
    """Vérifie si le compte appartient à une catégorie définie"""
    for f in filtres:
        if isinstance(f, str):
            if compte.startswith(f):
                return True
        elif isinstance(f, tuple) and len(f) == 2:
            try:
                val = int(compte)
                if int(f[0]) <= val <= int(f[1]):
                    return True
            except ValueError:
                continue
    return False

def generer_bilan(df):
    """Génère le bilan selon les catégories définies"""
    result = {}
    details = {}
    for categorie, filtres in CATEGORIES_BILAN.items():
        masque = df['Compte'].apply(lambda x: appartient_a(x, filtres))
        # Filtrer les comptes avec une valeur Solde non nulle
        comptes_non_nuls = df.loc[masque & (df['Solde'] != 0)]
        total = comptes_non_nuls['Solde'].sum()
        
        # Extraire les comptes, leurs noms et leurs montants
        comptes = comptes_non_nuls[['Compte', 'Nom du Compte', 'Solde']].copy()
        details[categorie] = comptes
        
        result[categorie] = total
    
    bilan_df = pd.DataFrame.from_dict(result, orient='index', columns=['Montant'])
    return bilan_df, details

def generer_compte_resultat(df):
    """Génère le compte de résultat"""
    result = {}
    details = {}
    for categorie, filtres in CATEGORIES_RESULTAT.items():
        masque = df['Compte'].apply(lambda x: appartient_a(x, filtres))
        # Filtrer les comptes avec une valeur Mouvement non nulle
        comptes_non_nuls = df.loc[masque & (df['Mouvement'] != 0)]
        total = comptes_non_nuls['Mouvement'].sum()

        # Extraire les comptes, leurs noms et leurs montants
        comptes = comptes_non_nuls[['Compte', 'Nom du Compte', 'Mouvement']].copy()
        details[categorie] = comptes
        
        result[categorie] = total
    
    resultat_df = pd.DataFrame.from_dict(result, orient='index', columns=['Montant'])
    return resultat_df, details

def exporter_rapports(df_bilan, df_resultat, bilan_details, resultat_details):
    """Exporte les rapports dans un fichier Excel"""
    # Ajouter "Résultat de l'exercice" au DataFrame avant l'exportation
    df_resultat.loc['Résultat de l\'exercice'] = df_resultat['Montant'].sum()

    with pd.ExcelWriter(FICHIER_SORTIE) as writer:
        # Préparer les données pour le Bilan
        bilan_output = pd.DataFrame(columns=['Compte', 'Désignation', 'Montant'])
        row_start_bilan = 0

        # Écrire les données du bilan
        for categorie, montant in df_bilan['Montant'].items():
            # Ignorer les catégories avec une valeur nulle
            if round(montant, 2) != 0:
                bilan_output.loc[row_start_bilan, 'Désignation'] = categorie
                bilan_output.loc[row_start_bilan, 'Montant'] = round(montant, 2)
                row_start_bilan += 1

                # Ajouter les détails des comptes
                if categorie in bilan_details:
                    comptes = bilan_details[categorie]
                    for index, compte in comptes.iterrows():
                        bilan_output.loc[row_start_bilan, 'Compte'] = compte['Compte']
                        bilan_output.loc[row_start_bilan, 'Désignation'] = compte['Nom du Compte']
                        bilan_output.loc[row_start_bilan, 'Montant'] = round(compte['Solde'], 2)
                        row_start_bilan += 1
                
                # Ajouter une ligne vide pour séparer les catégories
                bilan_output.loc[row_start_bilan, 'Compte'] = ''
                bilan_output.loc[row_start_bilan, 'Désignation'] = ''
                bilan_output.loc[row_start_bilan, 'Montant'] = ''
                row_start_bilan += 1

        # Écrire le Bilan dans Excel
        bilan_output.to_excel(writer, sheet_name='Bilan', index=False)

        # Préparer les données pour le Compte de Résultat
        resultat_output = pd.DataFrame(columns=['Compte', 'Désignation', 'Montant'])
        row_start_resultat = 0

        # Écrire les données du compte de résultat
        for categorie, montant in df_resultat['Montant'].items():
            # Ignorer les catégories avec une valeur nulle
            if round(montant, 2) != 0:
                resultat_output.loc[row_start_resultat, 'Désignation'] = categorie
                resultat_output.loc[row_start_resultat, 'Montant'] = round(montant, 2)
                row_start_resultat += 1

                # Ajouter les détails des comptes
                if categorie in resultat_details:
                    comptes = resultat_details[categorie]
                    for index, compte in comptes.iterrows():
                        resultat_output.loc[row_start_resultat, 'Compte'] = compte['Compte']
                        resultat_output.loc[row_start_resultat, 'Désignation'] = compte['Nom du Compte']
                        resultat_output.loc[row_start_resultat, 'Montant'] = round(compte['Mouvement'], 2)
                        row_start_resultat += 1
                
                # Ajouter une ligne vide pour séparer les catégories
                resultat_output.loc[row_start_resultat, 'Compte'] = ''
                resultat_output.loc[row_start_resultat, 'Désignation'] = ''
                resultat_output.loc[row_start_resultat, 'Montant'] = ''
                row_start_resultat += 1

        # Écrire le Compte de Résultat dans Excel
        resultat_output.to_excel(writer, sheet_name='Compte de Résultat', index=False)

# === MAIN ===

def main():
    print("📊 Génération des états financiers ...")
    
    df = charger_donnees()
    if df is None:
        print("Arrêt de la génération des états financiers.")
        return
    
    bilan, bilan_details = generer_bilan(df)
    resultat, resultat_details = generer_compte_resultat(df)
    exporter_rapports(bilan, resultat, bilan_details, resultat_details)
    
    print(f"✅ Rapports générés avec succès : {FICHIER_SORTIE}")

if __name__ == "__main__":
    main()
