#!/usr/bin/env bash

version=$(cat version.txt)

# Base image
docker buildx build --target linkding --platform linux/aarch64 \
  -f docker/default.Dockerfile \
  -t jmason/linkding:latest \
  -t jmason/linkding:$version \
  .

# docker buildx build --target linkding --platform linux/amd64,linux/arm64,linux/arm/v7 \
  # -f docker/alpine.Dockerfile \
  # -t jmason/linkding:latest-alpine \
  # -t jmason/linkding:$version-alpine \
  # --push .

# Plus image with support for single-file snapshots
# Needs checking if this works with ARMv7, excluded for now
# docker buildx build --target linkding-plus --platform linux/amd64,linux/arm64 \
  # -f docker/default.Dockerfile \
  # -t jmason/linkding:latest-plus \
  # -t jmason/linkding:$version-plus \
  # --push .
# 
# docker buildx build --target linkding-plus --platform linux/amd64,linux/arm64 \
  # -f docker/alpine.Dockerfile \
  # -t jmason/linkding:latest-plus-alpine \
  # -t jmason/linkding:$version-plus-alpine \
  # --push .
