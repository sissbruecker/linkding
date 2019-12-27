#!/usr/bin/env bash

rm -rf static
npm run build
python manage.py compilescss
python manage.py collectstatic --ignore=*.scss
python manage.py compilescss --delete-files
