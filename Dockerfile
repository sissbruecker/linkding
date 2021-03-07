FROM node:current-alpine AS NODEBUILD
# copy directory to /opt and work inside it
WORKDIR /opt
COPY . /opt
# run the npm portion of build-static script
RUN rm -rf static && mkdir -p static/
RUN npm install -g npm && \
    npm install && \
    npm run build


FROM python:3.9-slim AS PYTHONBUILD
# install missing system deps
RUN apt-get update && apt-get -y install build-essential mime-support libpcre3-dev libsass-dev mime-support
# set working dir
WORKDIR /etc/linkding
COPY requirements.prod.txt ./requirements.txt
# make a virtualenv, upgrade pip & wheel, install prod requirements
RUN mkdir /venv && \
    python -m venv --upgrade-deps --copies /venv && \
    /venv/bin/pip install --upgrade pip wheel && \
    /venv/bin/pip install -Ur requirements.txt
# run the python half of build-static script
COPY --from=NODEBUILD /opt/ .
RUN /venv/bin/python manage.py compilescss && \
    /venv/bin/python manage.py collectstatic --ignore=*.scss && \
    /venv/bin/python manage.py compilescss --delete-files


FROM python:3.9-slim as FINAL
WORKDIR /etc/linkding
# copy application code from PYTHONBUILD stage
COPY --from=PYTHONBUILD /etc/linkding  /etc/linkding
# copy virtualenv from PYTHONBUILD stage
COPY --from=PYTHONBUILD /venv /venv
# copy mime.types from PYTHONBUILD stage
COPY --from=PYTHONBUILD /etc/mime.types /etc/mime.types
# run bootstrap.sh
RUN mkdir -p data && \
    /venv/bin/python manage.py migrate && \
    /venv/bin/python manage.py generate_secret_key && \
    chown -R www-data: /etc/linkding/data
# expose port and run uwsgi server
EXPOSE 9090
CMD ["/venv/bin/uwsgi","/etc/linkding/uwsgi.ini"]
