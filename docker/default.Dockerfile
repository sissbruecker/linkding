FROM node:20-alpine AS node-build
WORKDIR /etc/linkding
# install build dependencies
COPY rollup.config.mjs postcss.config.js package.json package-lock.json ./
RUN npm ci
# copy files needed for JS build
COPY bookmarks/frontend ./bookmarks/frontend
COPY bookmarks/styles ./bookmarks/styles
# run build
RUN npm run build


FROM python:3.12.6-slim-bookworm AS build-deps
# Add required packages
# build-essential pkg-config: build Python packages from source
# libpq-dev: build Postgres client from source
# libicu-dev libsqlite3-dev: build Sqlite ICU extension
# llibffi-dev libssl-dev curl rustup: build Python cryptography from source
RUN apt-get update && apt-get -y install build-essential pkg-config libpq-dev libicu-dev libsqlite3-dev wget unzip libffi-dev libssl-dev curl
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
WORKDIR /etc/linkding
# install python dependencies
COPY requirements.txt requirements.txt
# Need to build psycopg2 from source for ARM platforms
RUN sed -i 's/psycopg2-binary/psycopg2/g' requirements.txt
RUN mkdir /opt/venv && \
    python -m venv --upgrade-deps --copies /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip wheel && \
    /opt/venv/bin/pip install -r requirements.txt


FROM build-deps AS compile-icu
# Defines SQLite version
# Since this is only needed for downloading the header files this probably
# doesn't need to be up-to-date, assuming the SQLite APIs used by the ICU
# extension do not change
ARG SQLITE_RELEASE_YEAR=2023
ARG SQLITE_RELEASE=3430000

# Compile the ICU extension needed for case-insensitive search and ordering
# with SQLite. This does:
# - Download SQLite amalgamation for header files
# - Download ICU extension source file
# - Compile ICU extension
RUN wget https://www.sqlite.org/${SQLITE_RELEASE_YEAR}/sqlite-amalgamation-${SQLITE_RELEASE}.zip && \
    unzip sqlite-amalgamation-${SQLITE_RELEASE}.zip && \
    cp sqlite-amalgamation-${SQLITE_RELEASE}/sqlite3.h ./sqlite3.h && \
    cp sqlite-amalgamation-${SQLITE_RELEASE}/sqlite3ext.h ./sqlite3ext.h && \
    wget https://www.sqlite.org/src/raw/ext/icu/icu.c?name=91c021c7e3e8bbba286960810fa303295c622e323567b2e6def4ce58e4466e60 -O icu.c && \
    gcc -fPIC -shared icu.c `pkg-config --libs --cflags icu-uc icu-io` -o libicu.so


FROM python:3.12.6-slim-bookworm AS linkding
LABEL org.opencontainers.image.source="https://github.com/sissbruecker/linkding"
# install runtime dependencies
RUN apt-get update && apt-get -y install mime-support libpq-dev libicu-dev libssl3 curl
WORKDIR /etc/linkding
# copy python dependencies
COPY --from=build-deps /opt/venv /opt/venv
# copy output from node build
COPY --from=node-build /etc/linkding/bookmarks/static bookmarks/static/
# copy compiled icu extension
COPY --from=compile-icu /etc/linkding/libicu.so libicu.so
# copy application code
COPY . .
# Activate virtual env
ENV VIRTUAL_ENV=/opt/venv
ENV PATH=/opt/venv/bin:$PATH
# Generate static files
RUN mkdir data && \
    python manage.py collectstatic

# Expose uwsgi server at port 9090
EXPOSE 9090
# Allow running containers as an an arbitrary user in the root group, to support deployment scenarios like OpenShift, Podman
RUN chmod g+w . && \
    chmod +x ./bootstrap.sh

HEALTHCHECK --interval=30s --retries=3 --timeout=1s \
CMD curl -f http://localhost:${LD_SERVER_PORT:-9090}/${LD_CONTEXT_PATH}health || exit 1

CMD ["./bootstrap.sh"]


FROM node:18-alpine AS ublock-build
WORKDIR /etc/linkding
# Install necessary tools
# Download and unzip the latest uBlock Origin Lite release
# Patch manifest to enable annoyances by default
# Patch ruleset-manager.js to use rulesets enabled in manifest by default
RUN apk add --no-cache curl jq unzip && \
    TAG=$(curl -sL https://api.github.com/repos/uBlockOrigin/uBOL-home/releases/latest | jq -r '.tag_name') && \
    DOWNLOAD_URL=https://github.com/uBlockOrigin/uBOL-home/releases/download/$TAG/$TAG.chromium.mv3.zip && \
    echo "Downloading $DOWNLOAD_URL" && \
    curl -L -o uBOLite.zip $DOWNLOAD_URL && \
    unzip uBOLite.zip -d uBOLite.chromium.mv3 && \
    rm uBOLite.zip && \
    jq '.declarative_net_request.rule_resources |= map(if .id == "annoyances-overlays" or .id == "annoyances-cookies" or .id == "annoyances-social" or .id == "annoyances-widgets" or .id == "annoyances-others" then .enabled = true else . end)' \
        uBOLite.chromium.mv3/manifest.json > temp.json && \
    mv temp.json uBOLite.chromium.mv3/manifest.json && \
    sed -i 's/const out = \[ '\''default'\'' \];/const out = await dnr.getEnabledRulesets();/' uBOLite.chromium.mv3/js/ruleset-manager.js


FROM linkding AS linkding-plus
# install chromium
RUN apt-get update && apt-get -y install chromium
# install node
ENV NODE_MAJOR=20
RUN apt-get install -y gnupg2 apt-transport-https ca-certificates && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /usr/share/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && apt-get install -y nodejs
# install single-file from fork for now, which contains several hotfixes
RUN npm install -g https://github.com/sissbruecker/single-file-cli/tarball/4c54b3bc704cfb3e96cec2d24854caca3df0b3b6
# copy uBlock
COPY --from=ublock-build /etc/linkding/uBOLite.chromium.mv3 uBOLite.chromium.mv3/
# create chromium profile folder for user running background tasks and set permissions
RUN mkdir -p chromium-profile &&  \
    chown -R www-data:www-data chromium-profile &&  \
    chown -R www-data:www-data uBOLite.chromium.mv3
# enable snapshot support
ENV LD_ENABLE_SNAPSHOTS=True
