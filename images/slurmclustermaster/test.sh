#!/bin/bash

#SBATCH --job-name=test
#SBATCH --output=res.txt
#SBATCH --ntasks=1

srun hostname
srun sleep 60