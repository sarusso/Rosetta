FROM lofar/lofar-pipeline:LOFAR-Release-4_0

# Set non-interactive
ENV DEBIAN_FRONTEND noninteractive

# Always update when extending base images
RUN apt update

#--------------
# Install deps
#---------------

# Git and Curl
RUN apt-get install git curl -y

# Install get-pip script
RUN curl -O https://bootstrap.pypa.io/get-pip.py

# Install Python and pip in this order (first Python 3 and then Python 2), or 
# you will end ap with python defaulting to python2 and pip defaulting to pip3
# Otherwise, do somethign like "ln -s /usr/local/bin/pip3 /usr/local/bin/pip"

# Install Python3 and Pip3 (python3-distutils required for pip3)
RUN apt install python3 python3-distutils -y 
RUN python3 get-pip.py 'pip==10.0.1'

# Install Python2 and Pip2
RUN apt install python -y
RUN python get-pip.py 'pip==10.0.1'

# Disable strict host checking for Github and Bitbucket
RUN mkdir ~/.ssh/
RUN echo "Host github.com\n\tStrictHostKeyChecking no\n" >> ~/.ssh/config


#------------------------
# Lofar user
#------------------------

# Add group. We chose GID 65527 to try avoiding conflicts.
RUN groupadd -g 65527 lofar

# Add user. We chose UID 65527 to try avoiding conflicts.
RUN useradd lofar -d /home/lofar -u 65527 -g 65527 -m -s /bin/bash

# Add metuaser user to sudoers
RUN adduser lofar sudo

# Install suodo
RUN apt-get install sudo -y

# No pass sudo (for everyone, actually)
COPY sudoers /etc/sudoers


#------------------------
# Get prefactor
#------------------------

#RUN cd /opt && git clone https://github.com/lofar-astron/prefactor
#RUN cd /opt/prefactor && git pull && git checkout 84596405369825ebdda8e302c2924ac8eaa69d3e # commit based on V3 to include fixes for Python3

RUN cd /opt && git clone https://github.com/sarusso/prefactor
RUN cd /opt/prefactor && git pull && git checkout cd7c12d596de54956c7cf351ecd28ca0ba7cddda # commit based on V3 to include fixes for Python3


# Add demo con and run scripts

COPY pipeline.cfg-demo /home/lofar/pipeline.cfg
COPY Pre-Facet-Calibrator.parset-demo /home/lofar/Pre-Facet-Calibrator.parset
COPY run_pipeline.sh /home/lofar/run_pipeline.sh
RUN chmod 755 -R /home/lofar/run_pipeline.sh && chown lofar:lofar /home/lofar

# Demo
#RUN cd /opt/prefactor/bin && python make_statistics.py

USER lofar
WORKDIR /home/lofar



