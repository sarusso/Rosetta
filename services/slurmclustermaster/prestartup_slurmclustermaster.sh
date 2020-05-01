#!/bin/bash
set -e

# Generic rosetta user shared folder
mkdir -p /shared/rosetta && chown rosetta:rosetta /shared/rosetta

# Shared home for slurmtestuser to simulate a shared home folders filesystem
cp -a /home_slurmtestuser_vanilla /shared/home_slurmtestuser
