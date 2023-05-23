#!/bin/bash

set -euo pipefail

# Remove previous container if exists
docker rm -f linkding-postgres-test || true

# Run postgres container
docker run -d \
  -e POSTGRES_DB=linkding \
  -e POSTGRES_USER=linkding \
  -e POSTGRES_PASSWORD=linkding \
  -p 5432:5432 \
  --name linkding-postgres-test \
  postgres

# Wait until postgres has started
echo >&2 "$(date +%Y%m%dt%H%M%S) Waiting for postgres container"
sleep 15

# Run tests using postgres
export LD_DB_ENGINE=postgres
export LD_DB_USER=linkding
export LD_DB_PASSWORD=linkding

./scripts/test.sh

# Remove postgres container
docker rm -f linkding-postgres-test || true
