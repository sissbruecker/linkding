#!/usr/bin/env bash

version=$(<version.txt)

git push origin master
git tag v${version}
git push origin v${version}
./scripts/build-docker.sh

echo "Done ✅"
