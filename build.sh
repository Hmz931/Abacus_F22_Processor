#!/bin/bash
set -o errexit

# Installer les dépendances système nécessaires
apt-get update
apt-get install -y python3-dev gcc

# Installer les dépendances Python
pip install --upgrade pip
pip install -r requirements.txt