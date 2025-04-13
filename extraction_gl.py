import pandas as pd
import numpy as np
from datetime import datetime
import re

# Dictionary to translate transaction origins
ORIGIN_TRANSLATIONS = {
    'F': 'Comptabilité financière (F11)',
    'CF': 'Comptabilité financière (F11)',
    'SF': 'Comptabilité financière (F11)',
    'K': "Programme de saisie des factures d'achat (K11)",
    'k': "Programme de paiement des factures d'achat",
    'L': 'Comptabilité de salaire',
    'Y': 'EBICS',
    'D': 'Débiteurs',
    'd': 'Débiteurs'
}

def extraire_nom_compte(feuille):
    """Extrait le nom de compte du nom de feuille (format '_6641_Frais_de_représentation')"""
    parties = feuille.split('_')
    if len(parties) >= 3:
        # Supprime les parties vides et prend tout après le numéro de compte
        parties_non_vides = [p for p in parties if p]
        if len(parties_non_vides) > 1:
            return ' '.join(parties_non_vides[1:]).replace('_', ' ').strip()
    return feuille  # Retourne le nom original si le format n'est pas reconnu

def detecter_colonnes_monnaie(df_columns):
    """Détecte automatiquement les colonnes Débit/Crédit selon la devise."""
    colonnes = df_columns.str.strip()

    # Détection des devises (EUR, USD, etc.)
    for col in colonnes:
        if 'EUR Débit' in col:
            return 'EUR Débit', 'EUR Crédit', 'EUR'
        elif 'USD Débit' in col:
            return 'USD Débit', 'USD Crédit', 'USD'
        elif 'GBP Débit' in col:
            return 'GBP Débit', 'GBP Crédit', 'GBP'

    # Par défaut CHF
    return 'Débit', 'Crédit', 'CHF'

def traduire_origine(origine):
    """Traduit le code d'origine en description complète."""
    return ORIGIN_TRANSLATIONS.get(origine, 'Inconnu')

def lire_reports_solde(fichier_input):
    """
    Lit les reports de solde et les périodes de chaque feuille dans le fichier Excel.
    """
    reports_solde = {}

    try:
        with pd.ExcelFile(fichier_input) as xls:
            for sheet_name in xls.sheet_names:
                try:
                    df_sheet = pd.read_excel(xls, sheet_name=sheet_name, header=None)

                    # Extraction de la période
                    period_row = df_sheet[df_sheet[0].astype(str).str.startswith('Solde ', na=False)]
                    period_string = period_row.iloc[0, 0] if not period_row.empty else None
                    if period_string:
                        period = period_string.replace("Solde ", "")
                        date_debut_str = period.split(" - ")[0] if " - " in period else period
                        try:
                            date_debut = datetime.strptime(date_debut_str, '%d.%m.%Y').date()
                        except ValueError:
                            print(f"Format de date incorrect pour la feuille {sheet_name}. Report de solde ignoré.")
                            date_debut = None
                    else:
                        date_debut = None

                    # Extraction du report de solde (cellule I4)
                    opening_balance = df_sheet.iloc[3, 8] if df_sheet.iloc[3, 8] is not None else 0
                    compte = sheet_name.split('_')[1] if '_' in sheet_name else sheet_name
                    libelle = f"Solde à nouveau de compte {compte}"

                    if date_debut:
                        reports_solde[sheet_name] = {
                            'Date': pd.Timestamp(date_debut),
                            'Libellé': libelle,
                            'Montant': opening_balance
                        }
                    else:
                        print(f"Période non trouvée pour la feuille {sheet_name}. Report de solde ignoré.")

                except Exception as e:
                    print(f"Erreur lors de la lecture de la feuille {sheet_name}: {str(e)}")
                    continue
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier Excel : {str(e)}")
        return {}

    return reports_solde

def traiter_feuille(df_input, sheet_name):
    """Traite une feuille du fichier Excel pour extraction des données."""
    print(f"Traitement de la feuille : {sheet_name} en cours...")

    # Nettoyer les noms de colonnes et détecter la devise
    df_input.columns = df_input.columns.str.strip()
    debit_col, credit_col, devise = detecter_colonnes_monnaie(df_input.columns)

    required_columns = ['Date doc', 'Texte', 'A', 'Document', debit_col, credit_col]
    missing_columns = set(required_columns) - set(df_input.columns)
    if missing_columns:
        print(f"Avertissement : Colonnes manquantes dans la feuille {sheet_name}: {missing_columns}")
        return None

    df_input = df_input[required_columns].copy()
    df_input.loc[:, 'Date doc'] = pd.to_datetime(df_input['Date doc'], format='%d.%m.%Y', errors='coerce')
    df_input.loc[:, debit_col] = pd.to_numeric(df_input[debit_col], errors='coerce').fillna(0)
    df_input.loc[:, credit_col] = pd.to_numeric(df_input[credit_col], errors='coerce').fillna(0)

    # Supprimer les lignes où "Débit" et "Crédit" sont toutes deux vides ou égales à zéro
    df_input = df_input[~((df_input[debit_col] == 0) & (df_input[credit_col] == 0))]

    numero_compte = sheet_name.split('_')[1] if '_' in sheet_name else sheet_name
    nom_compte = extraire_nom_compte(sheet_name)

    df_input['Compte'] = numero_compte
    df_input['Nom du Compte'] = nom_compte  # Nouvelle colonne ajoutée
    df_input['Feuille'] = sheet_name
    df_input['Devise'] = devise

    # Regrouper par document et calculer la somme des montants (Débit et Crédit)
    montants_par_document = df_input.groupby('Document')[[debit_col, credit_col]].sum().reset_index()
    montants_par_document = montants_par_document.rename(columns={debit_col: 'Total Débit', credit_col: 'Total Crédit'})

    # Fusionner les montants totaux par document avec le DataFrame original
    df_input = pd.merge(df_input, montants_par_document, on='Document', how='left')

    # Calculer le montant total pour chaque ligne
    df_input['Montant'] = df_input['Total Crédit'] + df_input['Total Débit']

    df_input['Origine_écriture'] = df_input['A'].map(traduire_origine)

    df_input = df_input.rename(columns={
        'Date doc': 'Date',
        'Texte': 'Libellé',
        'A': 'Origine',
        debit_col: 'Débit',
        credit_col: 'Crédit'
    })

    df_input = df_input[[
        'Date', 'Libellé', 'Compte', 'Nom du Compte', 'Montant', 'Devise',
        'Origine', 'Origine_écriture', 'Document', 'Débit', 'Crédit', 'Feuille'
    ]]

    return df_input

def nettoyer_donnees(dataframe):
    """
    Nettoie les données en supprimant les lignes sans valeur dans les colonnes 'Date', 'Libellé', 'Montant', 'Origine'
    et avec la valeur 'Inconnu' dans la colonne 'Origine_écriture'.
    """
    masque = (dataframe['Date'].isna()) & (dataframe['Libellé'].isna()) & (dataframe['Montant'].isna()) & (dataframe['Origine'].isna()) & (dataframe['Origine_écriture'] == 'Inconnu')

    dataframe_nettoye = dataframe[~masque]

    return dataframe_nettoye

def consolider_gl(fichier_input, fichier_output=None):
    """
    Consolide les données du grand livre à partir d'un fichier Excel.
    """
    if fichier_output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fichier_output = f"Grand_Livre_Consolidé_{timestamp}.xlsx"

    print(f"Début de la consolidation du fichier : {fichier_input}")
    reports_solde = lire_reports_solde(fichier_input)
    donnees_gl = []

    with pd.ExcelFile(fichier_input) as xls:
        for sheet_name in xls.sheet_names:
            print(f"Traitement de la feuille {sheet_name}...")
            try:
                df_input = pd.read_excel(xls, sheet_name=sheet_name)
                df_traite = traiter_feuille(df_input, sheet_name)

                if df_traite is not None:
                    donnees_gl.append(df_traite)

            except Exception as e:
                print(f"Erreur lors du traitement de la feuille {sheet_name}: {str(e)}")
                continue

    # Add opening balances to the consolidated data
    for sheet_name, solde_info in reports_solde.items():
        if not any(isinstance(df, pd.DataFrame) and (df['Feuille'] == sheet_name).any() for df in donnees_gl):
            if solde_info and 'Date' in solde_info and 'Libellé' in solde_info and 'Montant' in solde_info:
                nom_compte = extraire_nom_compte(sheet_name)
                opening_balance_data = {
                    'Date': solde_info['Date'],
                    'Libellé': solde_info['Libellé'],
                    'Compte': sheet_name.split('_')[1] if '_' in sheet_name else sheet_name,
                    'Nom du Compte': nom_compte,  # Ajout du nom de compte
                    'Montant': solde_info['Montant'],
                    'Devise': 'CHF',
                    'Origine': 'Report',
                    'Origine_écriture': 'Report de solde initial',
                    'Document': 'Solde initial',
                    'Débit': 0,
                    'Crédit': 0,
                    'Feuille': sheet_name
                }
                donnees_gl.append(pd.DataFrame([opening_balance_data]))

    if not donnees_gl:
        print("Aucune donnée à exporter.")
        return None

    gl_consolide = pd.concat(
        [df for df in donnees_gl if isinstance(df, pd.DataFrame)], ignore_index=True
    )
    
    gl_consolide['Date'] = pd.to_datetime(gl_consolide['Date'])
    gl_consolide = gl_consolide.sort_values(by='Date')

    gl_consolide = nettoyer_donnees(gl_consolide)

    sauvegarder_excel(gl_consolide, fichier_output)

    return gl_consolide

def sauvegarder_excel(dataframe, fichier_output):
    """
    Sauvegarde les données dans un fichier Excel formaté.
    """
    with pd.ExcelWriter(fichier_output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, index=False, sheet_name='Grand Livre')

        workbook = writer.book
        worksheet = writer.sheets['Grand Livre']

        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D9E1F2',
            'border': 1
        })

        for col_num, value in enumerate(dataframe.columns.values):
            worksheet.write(0, col_num, value, header_format)

        for i, col in enumerate(dataframe.columns):
            max_len = max(
                dataframe[col].astype(str).map(len).max(),
                len(str(col))
            )
            worksheet.set_column(i, i, max_len + 2)

        worksheet.autofilter(0, 0, len(dataframe), len(dataframe.columns) - 1)

    print(f"Le Grand Livre a été consolidé et sauvegardé dans : {fichier_output}")

def analyser_comptes(gl_consolide, fichier_input, fichier_output="soldes_par_feuille.xlsx"):
    """
    Analyse les comptes du grand livre consolidé et génère un rapport Excel.
    """
    resultats = []
    period_names = {}
    try:
        opening_balances = {}
        with pd.ExcelFile(fichier_input) as xls:
            for sheet_name in xls.sheet_names:
                try:
                    df_sheet = pd.read_excel(xls, sheet_name=sheet_name, header=None)

                    period_row = df_sheet[df_sheet[0].astype(str).str.startswith('Solde ', na=False)]
                    if not period_row.empty:
                        period_string = period_row.iloc[0, 0]
                        period_names[sheet_name] = period_string.replace("Solde ", "")
                    else:
                        period_names[sheet_name] = "Période inconnue"

                    try:
                        opening_balance = df_sheet.iloc[3, 8]
                        opening_balances[sheet_name] = opening_balance
                    except IndexError:
                        print(f"Avertissement : Cellule I4 non trouvée dans la feuille {sheet_name}. Définition du solde initial à 0.")
                        opening_balances[sheet_name] = 0
                except Exception as e:
                    print(f"Erreur lors de la lecture du report de solde pour la feuille {sheet_name}: {str(e)}")
                    opening_balances[sheet_name] = 0
                    period_names[sheet_name] = "Période inconnue"

    except Exception as e:
        print(f"Erreur lors de la lecture du fichier Excel : {str(e)}")
        opening_balances = {}
        period_names = {}

    for feuille in sorted(gl_consolide['Feuille'].unique()):
        mask = gl_consolide['Feuille'] == feuille
        debit = gl_consolide.loc[mask, 'Débit'].sum()
        credit = gl_consolide.loc[mask, 'Crédit'].sum()
        solde = debit - credit
        solde = np.round(solde, 2)

        report_solde = opening_balances.get(feuille, 0)
        solde_final = solde + report_solde
        solde_final = np.round(solde_final, 2)

        devise = gl_consolide.loc[mask, 'Devise'].unique()[0]

        compte = None
        match = re.search(r'[_*]?(\d+)[_*]?', feuille)
        if match:
            compte = match.group(1)

        nom_compte = gl_consolide.loc[mask, 'Nom du Compte'].unique()[0] if 'Nom du Compte' in gl_consolide.columns else extraire_nom_compte(feuille)

        if solde_final > 0:
            type_solde = 'Débiteur'
        elif solde_final < 0:
            type_solde = 'Créditeur'
        else:
            type_solde = 'Null'

        resultats.append({
            'Feuille': feuille,
            'Compte': compte,
            'Nom du Compte': nom_compte,  # Ajout du nom de compte
            'Total Débit': debit,
            'Total Crédit': credit,
            'Solde': solde,
            'Report Solde': report_solde,
            'Solde Final': solde_final,
            'Type': type_solde,
            'Devise': devise,
            'Période': period_names.get(feuille, "Période inconnue")
        })

    df_resultats = pd.DataFrame(resultats)

    period = period_names.get(df_resultats['Feuille'].iloc[0], "Période inconnue")
    end_date = period.split(" - ")[-1] if " - " in period else period

    solde_col_name = f"Solde {period}"
    solde_final_col_name = f"Solde au {end_date}"

    df_resultats = df_resultats.rename(columns={
        'Solde': solde_col_name,
        'Solde Final': solde_final_col_name
    })

    with pd.ExcelWriter(fichier_output, engine='xlsxwriter') as writer:
        df_resultats.to_excel(writer, sheet_name='Soldes', index=False)

        workbook = writer.book
        worksheet = writer.sheets['Soldes']

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        currency_format = workbook.add_format({'num_format': '###0.00'})
        green_format = workbook.add_format({'bg_color': '#CCFFCC'})
        red_format = workbook.add_format({'bg_color': '#FFCCCC'})
        null_format = workbook.add_format({'bg_color': '#FFFFCC'})

        for col_num, value in enumerate(df_resultats.columns.values):
            worksheet.write(0, col_num, value, header_format)

        worksheet.set_column('A:A', 30)  # Feuille
        worksheet.set_column('B:B', 10)  # Compte
        worksheet.set_column('C:C', 30)  # Nom du Compte (nouvelle colonne)
        worksheet.set_column('D:F', 15, currency_format)  # Montants
        worksheet.set_column('G:G', 15, currency_format)  # Report Solde
        worksheet.set_column('H:H', 15, currency_format)  # Solde Final
        worksheet.set_column('I:I', 12)  # Type
        worksheet.set_column('J:J', 30)  # Période
        worksheet.set_column('K:K', 10)  # Devise

        for row in range(1, len(df_resultats)+1):
            compte = str(df_resultats.at[row-1, 'Compte']) if pd.notna(df_resultats.at[row-1, 'Compte']) else ""
            type_val = df_resultats.at[row-1, 'Type']

            cell_format = None
            if type_val == 'Null':
                cell_format = null_format
            elif (compte.startswith('1') and type_val == 'Débiteur') or (compte.startswith('2') and type_val == 'Créditeur'):
                cell_format = green_format
            elif (compte.startswith('3') and type_val == 'Créditeur') or (compte.startswith('4') and type_val == 'Débiteur'):
                cell_format = green_format
            elif (compte.startswith('5') and type_val == 'Débiteur') or (compte.startswith('6') and type_val == 'Débiteur'):
                cell_format = green_format
            elif (compte.startswith('7') and type_val == 'Débiteur') or (compte.startswith('8') and type_val == 'Débiteur'):
                cell_format = green_format
            else:
                cell_format = red_format

            for col in range(len(df_resultats.columns)):
                worksheet.write(row, col, df_resultats.iloc[row-1, col], cell_format)

    print(f"Analyse des comptes sauvegardée dans : {fichier_output}")
    return df_resultats

if __name__ == "__main__":
    fichier_input = '2023_GL_NS.xlsx'
    fichier_output = 'Grand_Livre_Consolidé.xlsx'

    gl_consolide = consolider_gl(fichier_input, fichier_output)

    if gl_consolide is not None:
        analyser_comptes(gl_consolide, fichier_input, "soldes_par_feuille.xlsx")