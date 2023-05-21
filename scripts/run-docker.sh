#!/usr/bin/env bash

docker build -t sissbruecker/linkding:local .

docker rm -f linkding-local || true

docker run --name linkding-local --rm -p 9090:9090  \
  -e LD_SUPERUSER_NAME=admin \
  -e LD_SUPERUSER_PASSWORD=admin \
  sissbruecker/linkding:local
