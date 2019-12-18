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

Check status

	$ rosetta/ps


### Building errors

It is common for the build process to fail with a "404 not found" error on an apt-get instrucions, as apt repositories often change their IP addresses. In such case, try:

    $ rosetta/build nocache