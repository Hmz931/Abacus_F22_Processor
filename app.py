import os
from flask import Flask, render_template, request, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from extraction_gl import consolider_gl, analyser_comptes
from extraction_gl_EF import main as generer_etats_financiers
import pandas as pd

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xlsx'}

# Créer le dossier uploads s'il n'existe pas
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Vérifier si le fichier a été envoyé
        if 'file' not in request.files:
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Traiter le fichier
            try:
                # Étape 1: Consolider le grand livre
                gl_consolide = consolider_gl(filepath, "Grand_Livre_Consolidé.xlsx")
                
                if gl_consolide is not None:
                    # Étape 2: Analyser les comptes
                    df_soldes = analyser_comptes(gl_consolide, filepath, "soldes_par_feuille.xlsx")
                    
                    # Étape 3: Générer les états financiers
                    generer_etats_financiers()
                    
                    return redirect(url_for('results'))
                
            except Exception as e:
                return render_template('index.html', error=str(e))
    
    return render_template('index.html')

@app.route('/results')
def results():
    # Vérifier si les fichiers existent
    files = {
        'grand_livre': os.path.exists('Grand_Livre_Consolidé.xlsx'),
        'soldes': os.path.exists('soldes_par_feuille.xlsx'),
        'etats_financiers': os.path.exists('Rapports_Financiers.xlsx')
    }
    
    # Lire un aperçu des données pour affichage
    apercu = {}
    if files['grand_livre']:
        df = pd.read_excel('Grand_Livre_Consolidé.xlsx')
        apercu['grand_livre'] = df.head(5).to_html(classes='table table-striped')
    
    if files['soldes']:
        df = pd.read_excel('soldes_par_feuille.xlsx')
        apercu['soldes'] = df.head(5).to_html(classes='table table-striped')
    
    return render_template('results.html', files=files, apercu=apercu)

@app.route('/download/<filename>')
def download(filename):
    if filename in ['Grand_Livre_Consolidé.xlsx', 'soldes_par_feuille.xlsx', 'Rapports_Financiers.xlsx']:
        return send_file(filename, as_attachment=True)
    return "Fichier non trouvé", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)  # debug=False pour la production