#!/usr/bin/env bash

variant="${1:-default}"

docker build -f "docker/$variant.Dockerfile" -t sissbruecker/linkding:local .

docker rm -f linkding-local || true

docker run --name linkding-local --rm -p 9090:9090  \
  -e LD_SUPERUSER_NAME=admin \
  -e LD_SUPERUSER_PASSWORD=admin \
  sissbruecker/linkding:local
