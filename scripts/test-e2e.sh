#!/usr/bin/env bash

# Make sure Chromium is installed
playwright install chromium

# Test server loads assets from static folder, so make sure files there are up-to-date
rm -rf static
npm run build
python manage.py collectstatic

# Run E2E tests
python manage.py test bookmarks.e2e --pattern="e2e_test_*.py"
