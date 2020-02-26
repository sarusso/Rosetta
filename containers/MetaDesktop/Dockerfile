FROM ubuntu:18.04
MAINTAINER Stefano Alberto Russo <stefano.russo@gmail.com>

#----------------------
# Basics
#----------------------

# Set non-interactive
ENV DEBIAN_FRONTEND noninteractive

# Update first of all
RUN apt-get update

# Utilities
RUN apt-get install -y nano telnet unzip wget supervisor build-essential python-dev git-core openjdk-8-jre


#------------------------
# "Meta" user
#------------------------

# Add group. We chose GID 65527 to try avoiding conflicts.
RUN groupadd -g 65527 metauser

# Add user. We chose UID 65527 to try avoiding conflicts.
RUN useradd metauser -d /metauser -u 65527 -g 65527 -m -s /bin/bash

# Add metuaser user to sudoers
RUN adduser metauser sudo

# Install suodo
RUN apt-get install sudo -y

# No pass sudo (for everyone, actually)
COPY files/sudoers /etc/sudoers

#------------------------
# Supervisor conf
#------------------------

# Supervisord conf
COPY files/supervisord.conf /etc/supervisor/

#------------------------
# VNC
#------------------------

# Install xvfb that triggers minimal install of X base packages and xterm as sample application
RUN apt-get install xvfb xterm  -y

# Install base packages for VNC server and headless desktop (2)
RUN cd /opt && wget https://bintray.com/tigervnc/stable/download_file?file_path=tigervnc-1.8.0.x86_64.tar.gz -O tigervnc-1.8.0.x86_64.tar.gz \
            && tar -zxvf tigervnc-1.8.0.x86_64.tar.gz \
            && mv tigervnc-1.8.0.x86_64 tigervnc

# Supervisord configuration
COPY files/supervisord_vnc.conf /etc/supervisor/conf.d/
COPY files/run_vnc.sh /etc/supervisor/conf.d/
RUN chmod 755 /etc/supervisor/conf.d/run_vnc.sh


# Web VNC (noVNC) v0.6.1.
# NOTE: this is a custom version from Doro Wu (fcwu.tw@gmail.com).
# TODO: Check differences and maybe move to 0.6.2
COPY files/noVNC.tar.gz /usr/lib/
RUN cd /usr/lib/ && tar -zxvf noVNC.tar.gz
COPY files/index.html /usr/lib/noVNC

RUN apt-get install -y net-tools

# Supervisord configuration
COPY files/supervisord_webvnc.conf /etc/supervisor/conf.d/

# X environment setup/startup
RUN apt-get install fluxbox -y
COPY files/xstartup /opt/tigervnc/
RUN chmod 755 /opt/tigervnc/xstartup

# Prepare for logs
RUN mkdir /metauser/logs && chown metauser:metauser /metauser/logs

# Rename metauser home folder as a "vanilla" home folder
RUN mv /metauser /metauser_vanilla

# Add fluxbox customisations
COPY files/dot_fluxbox /metauser_vanilla/.fluxbox
RUN chown -R metauser:metauser /metauser_vanilla/.fluxbox
COPY files/background.jpg /usr/share/images/fluxbox/background.jpg


#----------------------
# Entrypoint
#----------------------

# Copy entrypoint
COPY files/entrypoint.sh /

# Give right permissions
RUN chmod 755 /entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Set user (mainly for Singularity)
USER metauser

# To access: expose 8590/tcp and 5900/tcp
