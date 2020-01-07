#!/bin/bash

DATE=$(date)

echo ""
echo "==================================================="
echo "  Starting Backend @ $DATE"
echo "==================================================="
echo ""

echo "1) Loading/sourcing env and settings"

# Load env
source /env.sh

# Database conf
source /db_conf.sh

# Django Project conf
if [[ "x$DJANGO_PROJECT_NAME" == "x" ]] ; then
    export DJANGO_PROJECT_NAME="Rosetta"
fi

if [[ "x$DJANGO_PUBLIC_HTTP_HOST" == "x" ]] ; then
    export DJANGO_PUBLIC_HTTP_HOST="https://rosetta.platform"
fi

if [[ "x$DJANGO_EMAIL_SERVICE" == "x" ]] ; then
    export DJANGO_EMAIL_SERVICE="Sendgrid"
fi

if [[ "x$DJANGO_EMAIL_FROM" == "x" ]] ; then
    export DJANGO_EMAIL_FROM="Rosetta <rosetta@rosetta.platform>"
fi

if [[ "x$DJANGO_EMAIL_APIKEY" == "x" ]] ; then
    export DJANGO_EMAIL_APIKEY=""
fi

# Set log levels
export DJANGO_LOG_LEVEL="CRITICAL"
export ROSETTA_LOG_LEVEL="CRITICAL"

# Stay quiet on Python warnings
export PYTHONWARNINGS=ignore

# To Python3 (unbuffered). P.s. "python3 -u" does not work..
export DJANGO_PYTHON=python3
export PYTHONUNBUFFERED=on

# Check if there is something to migrate or populate
echo ""
echo "2) Making migrations..."
cd /opt/webapp_code && $DJANGO_PYTHON manage.py makemigrations --noinput
EXIT_CODE=$?
echo "Exit code: $EXIT_CODE"
if [[ "x$EXIT_CODE" != "x0" ]] ; then
    echo "This exit code is an error, sleeping 5s and exiting." 
    sleep 5
    exit $?
fi
echo ""

echo "3) Migrating..."
cd /opt/webapp_code && $DJANGO_PYTHON manage.py migrate --noinput
EXIT_CODE=$?
echo "Exit code: $EXIT_CODE"
if [[ "x$EXIT_CODE" != "x0" ]] ; then
    echo "This exit code is an error, sleeping 5s and exiting." 
    sleep 5
    exit $?
fi
echo ""

echo "4) Populating base app..."
cd /opt/webapp_code && $DJANGO_PYTHON manage.py base_app_populate  
EXIT_CODE=$?
echo "Exit code: $EXIT_CODE"
if [[ "x$EXIT_CODE" != "x0" ]] ; then
    echo "This exit code is an error, sleeping 5s and exiting." 
    sleep 5
    exit $?
fi
echo ""

# Run the (development) server
echo "6) Now starting the server and logging in /var/log/cloud_server.log."
exec $DJANGO_PYTHON manage.py runserver 0.0.0.0:8080 2>> /var/log/webapp/server.log
