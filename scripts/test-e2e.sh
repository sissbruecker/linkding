#!/usr/bin/env bash

# Make sure Chromium is installed
uv run playwright install chromium

# Test server loads assets from static folder, so make sure files there are up-to-date
rm -rf static
npm run build
uv run manage.py collectstatic

# Run E2E tests
uv run manage.py test bookmarks.tests_e2e --pattern="e2e_test_*.py"
