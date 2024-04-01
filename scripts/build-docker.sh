#!/usr/bin/env bash

version=$(<version.txt)

# Base image
docker buildx build --target linkding --platform linux/amd64,linux/arm64,linux/arm/v7 \
  -f docker/default.Dockerfile \
  -t sissbruecker/linkding:latest \
  -t sissbruecker/linkding:$version \
  --push .

docker buildx build --target linkding --platform linux/amd64,linux/arm64,linux/arm/v7 \
  -f docker/alpine.Dockerfile \
  -t sissbruecker/linkding:latest-alpine \
  -t sissbruecker/linkding:$version-alpine \
  --push .

# Plus image with support for single-file snapshots
# Needs checking if this works with ARMv7, excluded for now
docker buildx build --target linkding-plus --platform linux/amd64,linux/arm64 \
  -f docker/default.Dockerfile \
  -t sissbruecker/linkding:latest-plus \
  -t sissbruecker/linkding:$version-plus \
  --push .

docker buildx build --target linkding-plus --platform linux/amd64,linux/arm64 \
  -f docker/alpine.Dockerfile \
  -t sissbruecker/linkding:latest-plus-alpine \
  -t sissbruecker/linkding:$version-plus-alpine \
  --push .
