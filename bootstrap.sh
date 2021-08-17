#!/usr/bin/env bash
# Bootstrap script that gets executed in new Docker containers

# Create data folder if it does not exist
mkdir -p data

# Run database migration
python manage.py migrate
# Generate secret key file if it does not exist
python manage.py generate_secret_key

# Ensure the DB folder is owned by the right user
chown -R www-data: /etc/linkding/data

# Start background task processor using supervisord
supervisord -c supervisord.conf

# Start uwsgi server
uwsgi uwsgi.ini
