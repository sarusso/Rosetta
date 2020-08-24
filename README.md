# Rosetta 🛰️


_A container-centric Science Platform_


Rosetta makes it easy to run interactive workloads on batch and remote computing systems using Docker and Singularity containers.


## Quickstart

Requirements:
    
    Bash, Git and Docker. Runs on Linux, Mac or Windows*.

*Windows not fully supported in development mode due to lack of support for symbolic links.

Setup

	$ rosetta/setup

Build

    $ rosetta/build

Run

	$ rosetta/run


Play

    You can now point your browser to http://localhost:8080.
    
    To run Slurm jobs use partition "partition1"

Clean

	# rosetta/clean

### Configuration

Example Webapp configuraion

      - SAFEMODE=False
      - DJANGO_LOG_LEVEL=CRITICAL
      - ROSETTA_LOG_LEVEL=ERROR
      - ROSETTA_TUNNEL_HOST=localhost # Not http or https
      - ROSETTA_WEBAPP_HOST= 
      - ROSETTA_WEBAPP_PORT=8080
      - LOCAL_DOCKER_REGISTRY_HOST=
      - LOCAL_DOCKER_REGISTRY_PORT=5000
      - DJANGO_EMAIL_APIKEY="<API KEY>"
      - DJANGO_EMAIL_FROM="Rosetta Platform <notifications@rosetta.platform>
      - DJANGO_PUBLIC_HTTP_HOST=http://localhost:8080 # Public facing, with shttp or https



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
    
## Known issues

    SINGULARITY_TMPDIR=/...
    .singularity in user home







