FROM rosetta/base
MAINTAINER Stefano Alberto Russo <stefano.russo@gmail.com>

# Install Slurm
RUN apt-get -y install slurm-wlm

# Explicitly create /var/run/ dirs
RUN mkdir -p /var/run/munge
RUN mkdir -p /var/run/slurm-wlm

# Add munge key and set permissions
COPY munge.key /etc/munge/munge.key
RUN chown munge:munge /etc/munge/munge.key
RUN chmod 0400 /etc/munge/munge.key

# Add munge daemon supervisord coinf
COPY supervisord_munge.conf /etc/supervisor/conf.d/

# Add Slurm conf
COPY slurm.conf /etc/slurm-llnl/slurm.conf

# TODO: why do we need this?
RUN ln -s /var/lib/slurm-llnl /var/lib/slurm-wlm 
RUN ln -s /var/log/slurm-llnl /var/log/slurm-wlm
