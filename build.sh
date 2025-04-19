#!/bin/bash
set -o errexit

# Configuration pour Render
export PIP_ROOT_USER_ACTION=ignore
export PYTHONPYCACHEPREFIX=/tmp/pycache

# Mise à jour des dépendances
python -m pip install --upgrade pip==23.3.2
pip install --no-cache-dir -r requirements.txt

# Création des répertoires nécessaires
mkdir -p uploads
chmod -R 700 uploads

# Nettoyage des éventuels fichiers temporaires
find . -name "*.xlsx" -type f -delete
rm -rf __pycache__/