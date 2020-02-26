# Rosetta 💁🏽


_A container-centric Science Platform_


Rosetta makes it easy to run interactive workloads on batch and remote computing systems using Docker and Singularity containers.


## Quickstart

Requirements:
    
    Bash, Git and Docker. Runs on Linux, Mac or Windows*.

*Windows not supported in development mode due to lack of support for symbolic links.

Setup

	$ rosetta/setup

Build

    $ rosetta/build

Run

	$ rosetta/run


Play

    You can now point your browser to http://localhost:8080

Clean

	# rosetta/clean

### Extras

Check status (not yet fully supported)

    # rosetta/status


Run Web App unit tests (with Rosetta running)

    ./run_webapp_unit_tests.sh


### Building errors

It is common for the build process to fail with a "404 not found" error on an apt-get instrucions, as apt repositories often change their IP addresses. In such case, try:

    $ rosetta/build nocache


### Development mode

Django development server is running on port 8080 of the "webapp" service.

To enable live code changes, add or comment out the following in docker-compose.yaml under the "volumes" section of the "webapp" service:

    - ./services/webapp/code:/opt/webapp_code
    
This will mount the code from services/webapp/code as a volume inside the webapp container itself allowing to make immediately effective codebase edits.

Note that when you edit the Django ORM model, you need to rerun the migrate the database, either by just rerunning the webapp service:

    $ rosetta/rerun webapp

..ora by entering in the webapp service container and manually migrate:

    $ rosetta/shell webapp
    $ source /env.sh
    $ source /db_conf.sh
    $ cd /opt/webapp_code
    $ python3 manage.py makemigrations
    $ python3 manage.py migrate  