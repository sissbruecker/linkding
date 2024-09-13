FROM node:18-alpine AS node-build
WORKDIR /etc/linkding
# install build dependencies
COPY rollup.config.mjs postcss.config.js package.json package-lock.json ./
RUN npm ci
# copy files needed for JS build
COPY bookmarks/frontend ./bookmarks/frontend
COPY bookmarks/styles ./bookmarks/styles
# run build
RUN npm run build


# Use 3.11 for now, as django4-background-tasks doesn't work with 3.12 yet
FROM python:3.11.8-alpine3.19 AS python-base
# Add required packages
# alpine-sdk linux-headers pkgconfig: build Python packages from source
# libpq-dev: build Postgres client from source
# icu-dev sqlite-dev: build Sqlite ICU extension
# libffi-dev openssl-dev rust cargo: build Python cryptography from source
RUN apk update && apk add alpine-sdk linux-headers libpq-dev pkgconfig icu-dev sqlite-dev libffi-dev openssl-dev rust cargo
WORKDIR /etc/linkding


FROM python-base AS python-build
# install build dependencies
COPY requirements.txt requirements.txt
RUN pip install -U pip && pip install -r requirements.txt
# copy files needed for Django build
COPY . .
COPY --from=node-build /etc/linkding .
# remove style sources
RUN rm -rf bookmarks/styles
# run Django part of the build
RUN mkdir data && \
    python manage.py collectstatic


FROM python-base AS prod-deps
COPY requirements.txt ./requirements.txt
# Need to build psycopg2 from source for ARM platforms
RUN sed -i 's/psycopg2-binary/psycopg2/g' requirements.txt
RUN mkdir /opt/venv && \
    python -m venv --upgrade-deps --copies /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip wheel && \
    /opt/venv/bin/pip install -r requirements.txt


FROM python-base AS compile-icu
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


FROM python:3.11.8-alpine3.19 AS linkding
LABEL org.opencontainers.image.source="https://github.com/sissbruecker/linkding"
# install runtime dependencies
RUN apk update && apk add bash curl icu libpq mailcap libssl3
# create www-data user and group
RUN set -x ; \
  addgroup -g 82 -S www-data ; \
  adduser -u 82 -D -S -G www-data www-data && exit 0 ; exit 1
WORKDIR /etc/linkding
# copy prod dependencies
COPY --from=prod-deps /opt/venv /opt/venv
# copy output from build stage
COPY --from=python-build /etc/linkding/static static/
# copy compiled icu extension
COPY --from=compile-icu /etc/linkding/libicu.so libicu.so
# copy application code
COPY . .
# Expose uwsgi server at port 9090
EXPOSE 9090
# Activate virtual env
ENV VIRTUAL_ENV /opt/venv
ENV PATH /opt/venv/bin:$PATH
# Allow running containers as an an arbitrary user in the root group, to support deployment scenarios like OpenShift, Podman
RUN chmod g+w . && \
    chmod +x ./bootstrap.sh

HEALTHCHECK --interval=30s --retries=3 --timeout=1s \
CMD curl -f http://localhost:${LD_SERVER_PORT:-9090}/${LD_CONTEXT_PATH}health || exit 1

CMD ["./bootstrap.sh"]


FROM node:18-alpine AS ublock-build
WORKDIR /etc/linkding
# Install necessary tools
RUN apk add --no-cache curl jq unzip
# Fetch the latest release tag
# Download the library
# Unzip the library
RUN TAG=$(curl -sL https://api.github.com/repos/gorhill/uBlock/releases/latest | jq -r '.tag_name') && \
    DOWNLOAD_URL=https://github.com/gorhill/uBlock/releases/download/$TAG/uBlock0_$TAG.chromium.zip && \
    curl -L -o uBlock0.zip $DOWNLOAD_URL && \
    unzip uBlock0.zip
# Patch assets.json to enable easylist-cookies by default
RUN curl -L -o ./uBlock0.chromium/assets/thirdparties/easylist/easylist-cookies.txt https://ublockorigin.github.io/uAssets/thirdparties/easylist-cookies.txt
RUN jq '."assets.json" |= del(.cdnURLs) | ."assets.json".contentURL = ["assets/assets.json"] | ."fanboy-cookiemonster" |= del(.off) | ."fanboy-cookiemonster".contentURL += ["assets/thirdparties/easylist/easylist-cookies.txt"]' ./uBlock0.chromium/assets/assets.json > temp.json && \
    mv temp.json ./uBlock0.chromium/assets/assets.json


FROM linkding AS linkding-plus
# install node, chromium
RUN apk update && apk add nodejs npm chromium
# install single-file from fork for now, which contains several hotfixes
RUN npm install -g https://github.com/sissbruecker/single-file-cli/tarball/4c54b3bc704cfb3e96cec2d24854caca3df0b3b6
# copy uBlock0
COPY --from=ublock-build /etc/linkding/uBlock0.chromium uBlock0.chromium/
# create chromium profile folder for user running background tasks
RUN mkdir -p chromium-profile && chown -R www-data:www-data chromium-profile
# enable snapshot support
ENV LD_ENABLE_SNAPSHOTS=True
