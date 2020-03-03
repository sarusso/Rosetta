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

if [[ "xDJANGO_DB_NAME" == "x:memory:" ]] ; then
    # Use the /tmp directory via links to use ephemeral data
    mkdir -p /tmp/migrations
    $MIGRATIONS_DATA_FOLDER=/tmp/migrations
    echo "Using temporary migrations in $MIGRATIONS_DATA_FOLDER"
else
    # Use the /data directory via links to use data persistency
    MIGRATIONS_DATA_FOLDER="/data/migrations"
    # Also if the migrations folder in /data does not exist, create it now
    mkdir -p /data/migrations
	echo "Persisting migrations in $MIGRATIONS_DATA_FOLDER"
fi


#-----------------------------
# Handle Base App migrations
#-----------------------------
	
# Remove potential leftovers
rm -f /opt/webapp_code/rosetta/base_app/migrations

# If migrations were not already initialized, do it now
if [ ! -d "$MIGRATIONS_DATA_FOLDER/base_app" ] ; then
    echo "Initializing migrations for base_app"...
    mkdir $MIGRATIONS_DATA_FOLDER/base_app && chown rosetta:rosetta $MIGRATIONS_DATA_FOLDER/base_app
    touch $MIGRATIONS_DATA_FOLDER/base_app/__init__.py && chown rosetta:rosetta $MIGRATIONS_DATA_FOLDER/base_app/__init__.py
fi

# Use the right migrations folder
ln -s $MIGRATIONS_DATA_FOLDER/base_app /opt/webapp_code/rosetta/base_app/migrations








