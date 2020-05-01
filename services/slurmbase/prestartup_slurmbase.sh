#!/bin/bash
set -e

# "Deactivate" local slurmtestuser home
mv /home/slurmtestuser /home_slurmtestuser_vanilla

# Link slurmtestuser against the home in the shared folder (which will be setup by the master node)
ln -s /shared/home_slurmtestuser /home/slurmtestuser
