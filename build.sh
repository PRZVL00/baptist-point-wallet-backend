#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
python manage.py create_superuser

# Load initial data if it exists
if [ -f data.json ]; then
    python manage.py loaddata data.json
fi