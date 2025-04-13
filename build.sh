#!/bin/bash
set -o errexit

# Solution pour l'erreur Read-only file system
export PIP_ROOT_USER_ACTION=ignore

# Installer les dépendances Python uniquement (sans apt-get)
python -m pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt