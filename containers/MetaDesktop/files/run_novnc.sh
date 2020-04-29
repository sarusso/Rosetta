#!/bin/bash

# Exec TigerVNC server 

if [ "x$TASK_PORT" == "x" ]; then
    /usr/lib/noVNC/utils/launch.sh --listen 8590
    echo "Running noVN on port 8590"
else
    /usr/lib/noVNC/utils/launch.sh --listen $TASK_PORT
    echo "Running noVN on port $TASK_PORT"

fi
