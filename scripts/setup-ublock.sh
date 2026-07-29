rm -rf uBOLite.chromium.mv3

# Download the latest uBlock Origin Lite release with a Chromium asset
DOWNLOAD_URL=$(curl -fsSL "https://api.github.com/repos/uBlockOrigin/uBOL-home/releases?per_page=20" | \
  jq -r 'first(.[] | .assets[] | select(.name | endswith(".chromium.zip")) | .browser_download_url) // empty')
test -n "$DOWNLOAD_URL" || exit 1
echo "Downloading $DOWNLOAD_URL"
curl -fL -o uBOLite.zip "$DOWNLOAD_URL"
unzip uBOLite.zip -d uBOLite.chromium.mv3
rm uBOLite.zip

# Enable annoyances rulesets in manifest.json
jq '.declarative_net_request.rule_resources |= map(if .id == "annoyances-overlays" or .id == "annoyances-cookies" or .id == "annoyances-social" or .id == "annoyances-widgets" or .id == "annoyances-others" then .enabled = true else . end)' uBOLite.chromium.mv3/manifest.json > temp.json
mv temp.json uBOLite.chromium.mv3/manifest.json

mkdir -p chromium-profile
