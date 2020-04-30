#!/bin/bash

# Exec TigerVNC server 

if [ "x$BASE_PORT" == "x" ]; then
    DESKTOP_NUMBER=0
else
    DESKTOP_NUMBER=$(($BASE_PORT-5900+1))
fi

if [ "x$VNC_AUTH" == "xTrue" ]; then
    /opt/tigervnc/usr/bin/vncserver :$DESKTOP_NUMBER -SecurityTypes vncauth,tlsvnc -xstartup /opt/tigervnc/xstartup
else
    /opt/tigervnc/usr/bin/vncserver :$DESKTOP_NUMBER -SecurityTypes None -xstartup /opt/tigervnc/xstartup
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
