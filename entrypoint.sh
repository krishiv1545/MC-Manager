#!/bin/sh

set -e

echo "Applying migrations..."
python backend/manage.py migrate --noinput

echo "Collecting static files..."
python backend/manage.py collectstatic --noinput

echo "Starting Django..."
exec python backend/manage.py runserver 0.0.0.0:8000