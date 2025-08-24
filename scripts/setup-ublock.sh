rm -rf uBOLite.chromium.mv3

# Download uBlock Origin Lite
TAG=$(curl -sL https://api.github.com/repos/uBlockOrigin/uBOL-home/releases/latest | jq -r '.tag_name')
DOWNLOAD_URL=https://github.com/uBlockOrigin/uBOL-home/releases/download/$TAG/$TAG.chromium.mv3.zip
echo "Downloading $DOWNLOAD_URL"
curl -L -o uBOLite.zip $DOWNLOAD_URL
unzip uBOLite.zip -d uBOLite.chromium.mv3
rm uBOLite.zip

# Enable annoyances rulesets in manifest.json
jq '.declarative_net_request.rule_resources |= map(if .id == "annoyances-overlays" or .id == "annoyances-cookies" or .id == "annoyances-social" or .id == "annoyances-widgets" or .id == "annoyances-others" then .enabled = true else . end)' uBOLite.chromium.mv3/manifest.json > temp.json
mv temp.json uBOLite.chromium.mv3/manifest.json

mkdir -p chromium-profile
