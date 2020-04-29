#!/bin/bash

# Exec TigerVNC server 

if [ "x$VNC_AUTH" == "xTrue" ]; then
    /opt/tigervnc/usr/bin/vncserver :0 -SecurityTypes vncauth,tlsvnc -xstartup /opt/tigervnc/xstartup
else
    /opt/tigervnc/usr/bin/vncserver :0 -SecurityTypes None -xstartup /opt/tigervnc/xstartup
fi


# Check it is running. If it is not, exit
while true
do

    PSOUT=$(ps -ef | grep /opt/tigervnc/usr/bin/Xvnc | grep SecurityTypes) 

    if [[ "x$PSOUT" == "x" ]] ; then
        exit 1
    fi

	# Sleep other 10 secs before re-checking
	sleep 10

done
