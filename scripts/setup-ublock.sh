#!/bin/sh
# Also used by the Docker builds to set up uBlock Origin Lite, see docker/*.Dockerfile
set -e

rm -rf uBOLite.chromium.mv3

# Download the latest stable uBlock Origin Lite release with a Chromium asset
DOWNLOAD_URL=$(curl -fsSL "https://api.github.com/repos/uBlockOrigin/uBOL-home/releases?per_page=20" | \
  jq -r 'first(.[] | select(.prerelease == false) | .assets[] | select(.name | endswith(".chromium.zip")) | .browser_download_url) // empty')
if [ -z "$DOWNLOAD_URL" ]; then
  echo "No uBlock Origin Lite release with a .chromium.zip asset found (or the GitHub API is unavailable / rate limited)" >&2
  exit 1
fi
echo "Downloading $DOWNLOAD_URL"
curl -fL -o uBOLite.zip "$DOWNLOAD_URL"
unzip uBOLite.zip -d uBOLite.chromium.mv3
rm uBOLite.zip

# Enable annoyances rulesets in manifest.json
jq '.declarative_net_request.rule_resources |= map(if .id == "annoyances-overlays" or .id == "annoyances-cookies" or .id == "annoyances-social" or .id == "annoyances-widgets" or .id == "annoyances-others" then .enabled = true else . end)' uBOLite.chromium.mv3/manifest.json > temp.json
mv temp.json uBOLite.chromium.mv3/manifest.json

mkdir -p chromium-profile
