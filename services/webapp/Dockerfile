FROM rosetta/base
MAINTAINER Stefano Alberto Russo <stefano.russo@gmail.com>

# Always start with an apt-get update when extending base images,
# otherwise apt repositories might get outdated (404 not found)
# and building without cache does not re-build base images.
RUN apt-get update

#------------------------------
# Apt requirements
#------------------------------

# Install Curl
RUN apt-get install curl -y

# Download get-pip script
RUN curl -O https://bootstrap.pypa.io/get-pip.py

# Install Python3 and Pip3 (python3-distutils required for pip3)
RUN apt-get install python3 python3-distutils -y 

# Install Python and pip in this order (first Python 3 and then Python 2), or 
# you will end ap with python defaulting to python2 and pip defaulting to pip3
# Otherwise, do somethign like "ln -s /usr/local/bin/pip3 /usr/local/bin/pip"

# Install Python3 and Pip3 (ython3-distutils required for pip3)
RUN apt-get install python3 python3-distutils -y 
RUN python3 get-pip.py 'pip==10.0.1'

# Install Python2 and Pip2
RUN apt-get install python -y
RUN python get-pip.py 'pip==10.0.1'

# Python 3 dev (for pycrypto)
RUN apt-get install python3-dev -y

# Install postgres driver required for psycopg2
RUN apt-get install libpq-dev -y

# Docker
RUN apt-get install docker.io -y

#------------------------------
# Install Django project
#------------------------------

# Prepare dir
RUN mkdir /opt/code

# Install Python requirements..
COPY requirements.txt /tmp/
RUN cd /opt/code && pip3 install -r /tmp/requirements.txt

# Patch Django 2.2 non-ascii chars in /usr/local/lib/python3.6/dist-packages/django/views/templates/technical_500.html
RUN sed -i 's/[\x80-\xFF]/./g' /usr/local/lib/python3.6/dist-packages/django/views/templates/technical_500.html

# Install App code
COPY code /opt/code

# Fix permissions
RUN chown -R rosetta:rosetta /opt/code

# Copy db conf
COPY db_conf.sh /db_conf.sh

# Prepare for logs
RUN mkdir /var/log/webapp/ && chown rosetta:rosetta /var/log/webapp/


#------------------------------
# Supervisord
#------------------------------

COPY run_webapp.sh /etc/supervisor/conf.d/
RUN chmod 755 /etc/supervisor/conf.d/run_webapp.sh
COPY supervisord_webapp.conf /etc/supervisor/conf.d/
COPY supervisord_dregistrytunnel.conf /etc/supervisor/conf.d/


#------------------------------
# Prestartup
#------------------------------

COPY prestartup_webapp.sh /prestartup/







