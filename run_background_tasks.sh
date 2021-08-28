#!/usr/bin/env bash
# Wrapper script used by supervisord to first clear task locks before starting the background task processor

python manage.py clean_tasks
exec python manage.py process_tasks
