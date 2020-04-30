#!/bin/bash

# Exec TigerVNC server 

if [ "x$BASE_PORT" == "x" ]; then
    /usr/lib/noVNC/utils/launch.sh --listen 8590
    echo "Running noVNC on port 8590"
else
    /usr/lib/noVNC/utils/launch.sh --listen $BASE_PORT --vnc localhost:$(($BASE_PORT+1))
    echo "Running noVNC on port $BASE_PORT and connecting to VNC on port $(($BASE_PORT+1))"

fi
