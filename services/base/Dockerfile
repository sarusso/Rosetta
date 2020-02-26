FROM ubuntu:18.04
MAINTAINER Stefano Alberto Russo <stefano.russo@gmail.com>

#----------------------
# Basics
#----------------------

# Set non-interactive
ENV DEBIAN_FRONTEND noninteractive

# Update
RUN apt-get update

# Utilities
RUN apt-get install -y nano telnet unzip wget supervisor openssh-server

# Devel
RUN apt-get install -y build-essential python-dev git-core

# Java
RUN apt-get install -y openjdk-8-jre

# IP utilities (mandatory for DNS!)
RUN apt-get install net-tools iproute2 iputils-ping -y


#------------------------
# Scienceuser user
#------------------------

# Add group. We chose GID 65527 to try avoiding conflicts.
RUN groupadd -g 65527 rosetta

# Add user. We chose UID 65527 to try avoiding conflicts.
RUN useradd rosetta -d /rosetta -u 65527 -g 65527 -m -s /bin/bash

# Add rosetta user to sudoers
RUN adduser rosetta sudo

# Keys
RUN mkdir /rosetta/.ssh
COPY keys/authorized_keys /rosetta/.ssh/
COPY keys/id_rsa /rosetta/.ssh/
RUN chmod 0600 /rosetta/.ssh/id_rsa
COPY keys/id_rsa.pub /rosetta/.ssh/
RUN chown -R rosetta:rosetta /rosetta/.ssh

# Install suodo
RUN apt-get install sudo -y

# No pass sudo (for everyone, actually)
COPY sudoers /etc/sudoers

# bash_profile for loading correct env (/env.sh created by entrypoint.sh)
RUN echo "source /env.sh" > /rosetta/.bash_profile


#------------------------
# Data, Logs and opt dirs
#------------------------

# Create dirs
RUN mkdir /data && mkdir /opt/rosetta && mkdir /var/log/rosetta 

# Give right permissions
RUN chown -R rosetta:rosetta /data && chown -R rosetta:rosetta /opt/rosetta && chown -R rosetta:rosetta /var/log/rosetta


#----------------------
#  Supervisord conf
#----------------------

COPY supervisord.conf /etc/supervisor/


#----------------------
# SSH conf
#----------------------

RUN mkdir /var/run/sshd && chmod 0755 /var/run/sshd
COPY supervisord_sshd.conf /etc/supervisor/conf.d/


#----------------------
# Prestartup scripts
#----------------------

# Create dir for prestartup scripts and copy main script
RUN mkdir /prestartup
COPY prestartup.py /


#----------------------
#  Singularity
#----------------------

# Dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    uuid-dev \
    libgpgme11-dev \
    squashfs-tools \
    libseccomp-dev \
    pkg-config \
    cryptsetup-bin \
    wget

# Install GO
RUN cd /tmp && wget https://dl.google.com/go/go1.11.linux-amd64.tar.gz
RUN cd /tmp && tar -zxf go1.11.linux-amd64.tar.gz && mv go /usr/local
ENV GOROOT=/usr/local/go
ENV GOPATH=/root/go
ENV PATH=$PATH:/usr/local/go/bin:$GOPATH/bin

# Install Singularity
RUN mkdir -p /usr/local/var/singularity/mnt && \
    mkdir -p $GOPATH/src/github.com/sylabs && \
    cd $GOPATH/src/github.com/sylabs && \
    wget https://github.com/sylabs/singularity/releases/download/v3.4.1/singularity-3.4.1.tar.gz && \
    tar -xzvf singularity-3.4.1.tar.gz
RUN cd $GOPATH/src/github.com/sylabs/singularity && \
    ./mconfig -p /usr/local && \
    make -C builddir && \
    make -C builddir install

# Build test image
RUN mkdir /singularity_images && chmod 777 /singularity_images
COPY testimage.def /singularity_images/testimage.def
RUN singularity build /singularity_images/testimage.simg /singularity_images/testimage.def


#----------------------
# Entrypoint
#----------------------

# Copy entrypoint
COPY entrypoint.sh /

# Give right permissions
RUN chmod 755 /entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]


