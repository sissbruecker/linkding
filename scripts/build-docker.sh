#!/usr/bin/env bash

version=$(<version.txt)

docker buildx build --platform linux/amd64,linux/arm64,linux/arm/v7 \
  -f docker/default.Dockerfile \
  -t sissbruecker/linkding:latest \
  -t sissbruecker/linkding:$version \
  --push .

docker buildx build --platform linux/amd64,linux/arm64,linux/arm/v7 \
  -f docker/alpine.Dockerfile \
  -t sissbruecker/linkding:latest-alpine \
  -t sissbruecker/linkding:$version-alpine \
  --push .
