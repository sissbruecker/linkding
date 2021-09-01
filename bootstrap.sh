#!/usr/bin/env bash
# Bootstrap script that gets executed in new Docker containers

LINKDING_PORT="${LINKDING_PORT:-9090}"

# Create data folder if it does not exist
mkdir -p data

# Run database migration
python manage.py migrate
# Generate secret key file if it does not exist
python manage.py generate_secret_key

# Ensure the DB folder is owned by the right user
chown -R www-data: /etc/linkding/data

# Start uwsgi server
uwsgi --http :$LINKDING_PORT uwsgi.ini
