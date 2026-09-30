#!/bin/bash
# ExamHub24 — deployment/update script for PythonAnywhere.
#
# Run this from the PythonAnywhere "Bash console" (or any Linux server) every time you
# pull new code, to apply migrations, collect static files, run tests, and remind you
# to reload the web app (PythonAnywhere doesn't allow scripts to reload the app for you
# on the free tier — that last step is manual via the Web tab).
#
# Usage:
#   chmod +x deploy.sh   (only needed once)
#   ./deploy.sh

set -e  # stop immediately if any command fails, instead of continuing with a broken deploy

echo "=================================================="
echo " ExamHub24 deployment"
echo "=================================================="

if [ -d "venv" ]; then
    echo "--> Activating virtual environment..."
    source venv/bin/activate
else
    echo "!! No venv/ folder found — activate your virtual environment manually first, then re-run this script."
    exit 1
fi

echo "--> Pulling latest code from git (skip if you deploy by uploading a zip instead)..."
if [ -d ".git" ]; then
    git pull
else
    echo "    (not a git repo — skipping)"
fi

echo "--> Installing/updating dependencies..."
pip install -r requirements.txt --quiet

echo "--> Running tests (deployment stops here if anything fails)..."
if command -v coverage &> /dev/null; then
    coverage run manage.py test --failfast
    coverage report -m
else
    python manage.py test --failfast
fi

echo "--> Applying database migrations..."
python manage.py makemigrations
python manage.py migrate

echo "--> Collecting static files..."
python manage.py collectstatic --noinput

echo "=================================================="
echo " Code deployed. Now go to the PythonAnywhere Web tab"
echo " and click the green 'Reload' button to apply changes."
echo "=================================================="
