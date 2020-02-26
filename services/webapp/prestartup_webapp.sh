#!/bin/bash
set -e

# Set proper permissions to the log dir
chown rosetta:rosetta /var/log/webapp

# Create and set proper permissions to the data/resources
mkdir -p /data/resources 
chown rosetta:rosetta /data/resources

#-----------------------------
# Set migrations data folder
#-----------------------------

if [[ "x$(mount | grep /devmigrations)" == "x" ]] ; then
    # If the migrations folder is not mounted (not a Docker volume), use the /data directory via links to use data persistency
    MIGRATIONS_DATA_FOLDER="/data/migrations"
    # Also if the migrations folder in /data does not exist, create it now
    mkdir -p /data/migrations
else
    # If the migrations folder is mounted (a Docker volume), use it as we are in dev mode
    MIGRATIONS_DATA_FOLDER="/devmigrations"
fi
echo "Persisting migrations in $MIGRATIONS_DATA_FOLDER"


#-----------------------------
# Handle Base App migrations
#-----------------------------

# Remove potential leftovers
rm -f /opt/webapp_code/rosetta/base_app/migrations
if [ ! -d "$MIGRATIONS_DATA_FOLDER/base_app" ] ; then
    # If migrations were not already initialized, do it now
    echo "Initializing migrations for base_app"...
    mkdir $MIGRATIONS_DATA_FOLDER/base_app && chown rosetta:rosetta $MIGRATIONS_DATA_FOLDER/base_app
    touch $MIGRATIONS_DATA_FOLDER/base_app/__init__.py && chown rosetta:rosetta $MIGRATIONS_DATA_FOLDER/base_app/__init__.py
fi

# Use the persisted migrations
ln -s $MIGRATIONS_DATA_FOLDER/base_app /opt/webapp_code/rosetta/base_app/migrations








