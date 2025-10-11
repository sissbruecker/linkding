#!/usr/bin/env bash

# Remove previous container if exists
docker rm -f linkding-postgres-test || true

# Run postgres container
docker run -d \
  -e POSTGRES_DB=linkding \
  -e POSTGRES_USER=linkding \
  -e POSTGRES_PASSWORD=linkding \
  -p 5432:5432 \
  -v $(pwd)/tmp/postgres-data:/var/lib/postgresql/data \
  --name linkding-postgres-test \
  postgres

# Wait until postgres has started
echo >&2 "$(date +%Y%m%dt%H%M%S) Waiting for postgres container"
sleep 15

# Start linkding dev server
export LD_DB_ENGINE=postgres
export LD_DB_USER=linkding
export LD_DB_PASSWORD=linkding

export LD_SUPERUSER_NAME=admin
export LD_SUPERUSER_PASSWORD=admin

uv run manage.py migrate
uv run manage.py create_initial_superuser
uv run manage.py runserver
