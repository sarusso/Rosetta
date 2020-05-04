#!/bin/bash

# Source env
source /env.sh

# Exec Apache in foreground
exec /usr/sbin/apache2ctl -DFOREGROUND

# Or just use in supervisord:
#/bin/bash -c "source /etc/apache2/envvars && source /env.sh && exec /usr/sbin/apache2 -DFOREGROUND"

