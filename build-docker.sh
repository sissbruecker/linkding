#!/usr/bin/env bash

./build-static.sh
docker buildx build --platform linux/amd64,linux/arm64,linux/arm/v7 -t sissbruecker/linkding:latest --push .
