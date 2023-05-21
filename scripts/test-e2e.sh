#!/usr/bin/env bash

# Make sure Chromium is installed
playwright install chromium

# Test server loads assets from static folder, so make sure files there are up-to-date
rm -rf static
npm run build
python manage.py compilescss
python manage.py collectstatic --ignore=*.scss
python manage.py compilescss --delete-files

# Run E2E tests
python manage.py test bookmarks.e2e --pattern="e2e_test_*.py"
