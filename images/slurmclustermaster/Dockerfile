FROM rosetta/slurmcluster
MAINTAINER Stefano Alberto Russo <stefano.russo@gmail.com>

# Configure supervisord to run SLURM
COPY supervisord_slurm* /etc/supervisor/conf.d/

# Add sample job script
COPY test.sh /rosetta

# Add prestartup
COPY prestartup_slurmclustermaster.sh /prestartup/
