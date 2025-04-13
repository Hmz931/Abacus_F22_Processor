#!/bin/bash
set -o errexit

# Solution définitive pour Render
export PIP_ROOT_USER_ACTION=ignore
export PYTHONPYCACHEPREFIX=/tmp/pycache

python -m pip install --upgrade pip==23.3.2
pip install --no-cache-dir -r requirements.txt