#!/usr/bin/env bash

source scripts/load-env-files.sh || exit 1
load_env_files LD_SERVER_PORT_FILE LD_CONTEXT_PATH_FILE || exit 1

curl -f "http://localhost:${LD_SERVER_PORT:-9090}/${LD_CONTEXT_PATH}health" || exit 1
