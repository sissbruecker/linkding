#!/usr/bin/env bash
# Bootstrap script that gets executed in new Docker containers

LD_SERVER_HOST="${LD_SERVER_HOST:-[::]}"
LD_SERVER_PORT="${LD_SERVER_PORT:-9090}"

# Create data folder if it does not exist
mkdir -p data
# Create favicon folder if it does not exist
mkdir -p data/favicons
# Create previews folder if it does not exist
mkdir -p data/previews
# Create assets folder if it does not exist
mkdir -p data/assets

# Generate secret key file if it does not exist
python manage.py generate_secret_key
# Run database migration
python manage.py migrate
# Enable WAL journal mode for SQLite databases
python manage.py enable_wal
# Create initial superuser if defined in options / environment variables
python manage.py create_initial_superuser
# Migrate legacy background tasks to Huey
python manage.py migrate_tasks

# Ensure folders are owned by the right user
chown -R www-data: /etc/linkding/data

# Start processes
# Experimental: use supervisor to manage all processes, enables logging background tasks to stdout/stderr
if [ "$LD_SUPERVISOR_MANAGED" = "True" ]; then
  exec supervisord -c supervisord-all.conf
# Default: start background task processor as daemon, then uwsgi as main process
else
  if [ "$LD_DISABLE_BACKGROUND_TASKS" != "True" ]; then
    supervisord -c supervisord-tasks.conf
  fi
  exec uwsgi --http $LD_SERVER_HOST:$LD_SERVER_PORT uwsgi.ini
fi
