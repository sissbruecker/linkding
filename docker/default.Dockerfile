FROM node:18-alpine AS node-build
WORKDIR /etc/linkding
# install build dependencies
COPY rollup.config.mjs package.json package-lock.json ./
RUN npm ci
# copy files needed for JS build
COPY bookmarks/frontend ./bookmarks/frontend
# run build
RUN npm run build


# Use 3.11 for now, as django4-background-tasks doesn't work with 3.12 yet
FROM python:3.11.8-slim-bookworm AS python-base
# Add required packages
# build-essential pkg-config: build Python packages from source
# libpq-dev: build Postgres client from source
# libicu-dev libsqlite3-dev: build Sqlite ICU extension
# llibffi-dev libssl-dev curl rustup: build Python cryptography from source
RUN apt-get update && apt-get -y install build-essential pkg-config libpq-dev libicu-dev libsqlite3-dev wget unzip libffi-dev libssl-dev curl
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
WORKDIR /etc/linkding


FROM python-base AS python-build
# install build dependencies
COPY requirements.txt requirements.txt
COPY requirements.dev.txt requirements.dev.txt
# remove playwright from requirements as there is not always a distro and it's not needed for the build
RUN sed -i '/playwright/d' requirements.dev.txt
RUN pip install -U pip && pip install -r requirements.txt -r requirements.dev.txt
# copy files needed for Django build
COPY . .
COPY --from=node-build /etc/linkding .
# run Django part of the build
RUN python manage.py compilescss && \
    python manage.py collectstatic --ignore=*.scss && \
    python manage.py compilescss --delete-files


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


FROM python:3.11.8-slim-bookworm as final
RUN apt-get update && apt-get -y install mime-support libpq-dev libicu-dev libssl3 curl
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
RUN ["chmod", "g+w", "."]
# Run bootstrap logic
RUN ["chmod", "+x", "./bootstrap.sh"]

HEALTHCHECK --interval=30s --retries=3 --timeout=1s \
CMD curl -f http://localhost:${LD_SERVER_PORT:-9090}/${LD_CONTEXT_PATH}health || exit 1

CMD ["./bootstrap.sh"]
