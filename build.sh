#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Initializing database & directories..."
python -c "import os; os.makedirs('instance', exist_ok=True); os.makedirs('backups', exist_ok=True); os.makedirs('images/uploads', exist_ok=True); import app, models; ctx = app.app.app_context(); ctx.push(); models.db.create_all()"

echo "Build complete!"
