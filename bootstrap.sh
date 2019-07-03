#!/usr/bin/env bash
# Bootstrap script that gets executed in new Docker containers

# Set host name in settings if it was passed as environment variable
if [[ -v HOST_NAME ]]
then
    printf "ALLOWED_HOSTS=['%s']" $HOST_NAME > ./siteroot/settings_custom.py
fi

# Run database migration
python manage.py migrate

# Start uwsgi server
uwsgi uwsgi.ini
