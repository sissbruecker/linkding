FROM node:18.13.0-alpine AS node-build
WORKDIR /etc/linkding
# install build dependencies
COPY package.json package-lock.json ./
RUN npm install -g npm && \
    npm install
# compile JS components
COPY . .
RUN npm run build


FROM python:3.10.6-slim-buster AS python-base
RUN apt-get update && apt-get -y install build-essential libpq-dev
WORKDIR /etc/linkding


FROM python-base AS python-build
# install build dependencies
COPY requirements.txt requirements.txt
RUN pip install -U pip && pip install -Ur requirements.txt
# run Django part of the build
COPY --from=node-build /etc/linkding .
RUN python manage.py compilescss && \
    python manage.py collectstatic --ignore=*.scss && \
    python manage.py compilescss --delete-files


FROM python-base AS prod-deps
COPY requirements.prod.txt ./requirements.txt
RUN mkdir /opt/venv && \
    python -m venv --upgrade-deps --copies /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip wheel && \
    /opt/venv/bin/pip install -Ur requirements.txt


FROM python:3.10.6-slim-buster as final
RUN apt-get update && apt-get -y install mime-support libpq-dev curl
WORKDIR /etc/linkding
# copy prod dependencies
COPY --from=prod-deps /opt/venv /opt/venv
# copy output from build stage
COPY --from=python-build /etc/linkding/static static/
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
