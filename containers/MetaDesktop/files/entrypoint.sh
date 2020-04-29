#!/bin/bash

# Exit on any error. More complex thing could be done in future
# (see https://stackoverflow.com/questions/4381618/exit-a-script-on-error)
set -e

echo ""
echo "[INFO] Executing entrypoint..."

#---------------------
#   Setup home
#---------------------

# First try without sudo (Singularity with --writable-tmpfs), then sudo (Docker)
echo "[INFO] Setting up home"

# Get immune to -e inside the curly brackets
{
  cp -a /metauser_vanilla /metauser &> /dev/null
  EXIT_CODE=$?
} || true

# Check if the above failed and we thus have to use sudo
if [ "$EXIT_CODE" != "0" ]; then
    #echo "Using sudo"
    sudo cp -a /metauser_vanilla /metauser
fi

# Manually set home (mainly for Singularity)
echo "[INFO] Setting up HOME env var"
export HOME=/metauser
cd /metauser

#---------------------
#   Save env
#---------------------
echo "[INFO] Dumping env"

# Save env vars for later usage (e.g. ssh)

env | \
while read env_var; do
  if [[ $env_var == HOME\=* ]]; then
      : # Skip HOME var
  elif [[ $env_var == PWD\=* ]]; then
      : # Skip PWD var
  else
      echo "export $env_var" >> /tmp/env.sh
  fi
done

#---------------------
#   Password
#---------------------

if [ "x$AUTH_PASS" != "x" ]; then
    echo "[INFO] Setting up VNC password..."
    mkdir -p /metauser/.vnc
    /opt/tigervnc/usr/bin/vncpasswd -f <<< $AUTH_PASS > /metauser/.vnc/passwd
    chmod 600 /metauser/.vnc/passwd
    export VNC_AUTH=True
else
    echo "[INFO] Not setting up any VNC password"
        
fi


#---------------------
#  Entrypoint command
#---------------------

if [ "$@x" == "x" ]; then
    DEFAULT_COMMAND="supervisord -c /etc/supervisor/supervisord.conf"
    echo -n "[INFO] Executing default entrypoint command: "
    echo $DEFAULT_COMMAND
    exec $DEFAULT_COMMAND
else
    echo -n "[INFO] Executing entrypoint command: "
    echo $@
    exec $@
fi 


