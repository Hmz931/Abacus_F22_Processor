import os
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from werkzeug.utils import secure_filename
from extraction_gl import consolider_gl, analyser_comptes
from extraction_gl_EF import exporter_rapports, generer_bilan, generer_compte_resultat, charger_donnees
import pandas as pd
from threading import Thread
import time

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xlsx'}
app.secret_key = os.urandom(24)

# Global processing status
processing_status = {
    'current': 0,
    'total': 0,
    'message': '',
    'completed': False,
    'error': None
}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def background_processing(filepath):
    global processing_status
    try:
        # Step 1: Count sheets
        with pd.ExcelFile(filepath) as xls:
            total_sheets = len(xls.sheet_names)
        
        processing_status['total'] = total_sheets
        processing_status['message'] = 'Analyse de la structure du fichier...'
        
        # Step 2: Consolidate GL
        processing_status['message'] = 'Consolidation du grand livre...'
        gl_consolide = consolider_gl(filepath, "Grand_Livre_Consolidé.xlsx")
        processing_status['current'] = total_sheets // 3
        
        # Step 3: Analyze accounts
        processing_status['message'] = 'Analyse des soldes comptables...'
        df_soldes = analyser_comptes(gl_consolide, filepath, "soldes_par_feuille.xlsx")
        processing_status['current'] = total_sheets // 3 * 2
        
        # Step 4: Financial statements
        processing_status['message'] = 'Génération des états financiers...'
        df = charger_donnees()
        bilan, bilan_details = generer_bilan(df)
        resultat, resultat_details = generer_compte_resultat(df)
        exporter_rapports(bilan, resultat, bilan_details, resultat_details)
        
        # Finalize
        processing_status['current'] = total_sheets
        processing_status['message'] = 'Traitement terminé avec succès!'
        processing_status['completed'] = True
        
    except Exception as e:
        processing_status['error'] = str(e)
        processing_status['message'] = f'Erreur: {str(e)}'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/progress')
def progress():
    return jsonify(processing_status)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Type de fichier non autorisé'}), 400
    
    # Reset processing status
    global processing_status
    processing_status = {
        'current': 0,
        'total': 0,
        'message': 'Initialisation...',
        'completed': False,
        'error': None
    }
    
    # Save file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file.save(filepath)
    
    # Start background processing
    thread = Thread(target=background_processing, args=(filepath,))
    thread.start()
    
    return jsonify({'status': 'processing_started'})

@app.route('/results')
def results():
    # Check existing files
    files = {
        'grand_livre': os.path.exists('Grand_Livre_Consolidé.xlsx'),
        'soldes': os.path.exists('soldes_par_feuille.xlsx'),
        'etats_financiers': os.path.exists('Rapports_Financiers.xlsx')
    }
    
    # Load data if files exist
    soldes_data = None
    rapports_data = None
    
    if files['soldes']:
        try:
            soldes_df = pd.read_excel('soldes_par_feuille.xlsx', sheet_name='Soldes')
            soldes_df = soldes_df.dropna(subset=['Feuille'])
            soldes_df['Total Débit'] = soldes_df['Total Débit'].fillna(0)
            soldes_df['Total Crédit'] = soldes_df['Total Crédit'].fillna(0)
            soldes_df['Solde Final'] = soldes_df['Solde Final'].fillna(0)
            soldes_data = soldes_df.to_dict('records')
        except Exception as e:
            app.logger.error(f"Erreur lecture soldes: {str(e)}")
            soldes_data = None
    
    if files['etats_financiers']:
        try:
            bilan_df = pd.read_excel('Rapports_Financiers.xlsx', sheet_name='Bilan')
            compte_resultat_df = pd.read_excel('Rapports_Financiers.xlsx', sheet_name='Compte de Résultat')
            
            bilan_df = bilan_df.dropna(subset=['Désignation'])
            compte_resultat_df = compte_resultat_df.dropna(subset=['Désignation'])
            
            rapports_data = {
                'bilan': bilan_df.to_dict('records'),
                'compte_resultat': compte_resultat_df.to_dict('records')
            }
        except Exception as e:
            app.logger.error(f"Erreur lecture rapports: {str(e)}")
            rapports_data = None
    
    return render_template(
        'results.html',
        files=files,
        soldes_data=soldes_data,
        rapports_data=rapports_data
    )

@app.route('/download/<filename>')
def download(filename):
    safe_files = {
        'grand_livre': 'Grand_Livre_Consolidé.xlsx',
        'soldes': 'soldes_par_feuille.xlsx',
        'rapports': 'Rapports_Financiers.xlsx'
    }
    if filename in safe_files and os.path.exists(safe_files[filename]):
        return send_file(safe_files[filename], as_attachment=True)
    return "Fichier non trouvé", 404

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message="Page non trouvée"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', message="Erreur interne du serveur"), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)