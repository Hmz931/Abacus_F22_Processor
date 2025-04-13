#!/bin/bash
set -o errexit

# Install system dependencies
apt-get update
apt-get install -y python3-dev gcc libpq-dev

# Upgrade pip and install Python packages
python -m pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt