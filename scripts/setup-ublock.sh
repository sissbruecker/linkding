rm -rf ublock0.chromium

TAG=$(curl -sL https://api.github.com/repos/gorhill/uBlock/releases/latest | jq -r '.tag_name')
DOWNLOAD_URL=https://github.com/gorhill/uBlock/releases/download/$TAG/uBlock0_$TAG.chromium.zip
curl -L -o uBlock0.zip $DOWNLOAD_URL
unzip uBlock0.zip
rm uBlock0.zip

curl -L -o ./uBlock0.chromium/assets/thirdparties/easylist/easylist-cookies.txt https://ublockorigin.github.io/uAssets/thirdparties/easylist-cookies.txt
jq '."assets.json" |= del(.cdnURLs) | ."assets.json".contentURL = ["assets/assets.json"] | ."fanboy-cookiemonster" |= del(.off) | ."fanboy-cookiemonster".contentURL += ["assets/thirdparties/easylist/easylist-cookies.txt"]' ./uBlock0.chromium/assets/assets.json > temp.json
mv temp.json ./uBlock0.chromium/assets/assets.json

mkdir -p chromium-profile
