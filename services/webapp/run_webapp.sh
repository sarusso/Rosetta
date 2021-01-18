#!/bin/bash

DATE=$(date)

echo ""
echo "==================================================="
echo "  Starting Webapp @ $DATE"
echo "==================================================="
echo ""

echo "Loading/sourcing env and settings..."
echo ""

# Load env
source /env.sh

# Database conf
source /db_conf.sh

# Stay quiet on Python warnings
export PYTHONWARNINGS=ignore

# To Python3 (unbuffered). P.s. "python3 -u" does not work..
export PYTHONUNBUFFERED=on

# Apply migrations if any
# Note: this will also indirectly wait for the DB to become up and reachable
echo "Applying migrations if any..."
cd /opt/code && python3 manage.py migrate --noinput
EXIT_CODE=$?
echo "Exit code: $EXIT_CODE"
if [[ "x$EXIT_CODE" != "x0" ]] ; then
    echo "This exit code is an error, sleeping 5s and exiting." 
    sleep 5
    exit $?
fi
echo ""


if [[ "x$DJANGO_DEV_SERVER" == "xTrue" ]] ; then
    
# Run the (development) server
    echo "Now starting the development server and logging in /var/log/webapp/server.log."
    exec python3 manage.py runserver 0.0.0.0:8080 2>> /var/log/webapp/server.log

else
    # Move to the code dir
    cd /opt/code
    
    # Collect static
    echo "Collecting static files..."
    python3 manage.py collectstatic

    # Run uWSGI
    echo "Now starting the uWSGI server and logging in /var/log/webapp/server.log."

	uwsgi --chdir=/opt/code \
	      --module=rosetta.wsgi \
	      --env DJANGO_SETTINGS_MODULE=rosetta.settings \
	      --master --pidfile=/tmp/project-master.pid \
	      --socket=127.0.0.1:49152 \
	      --static-map /static=/rosetta/static \
	      --http :8080 \
	      --disable-logging 2>> /var/log/webapp/server.log
fi


















