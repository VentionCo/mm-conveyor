#!/bin/bash

cd /var/lib/cloud9/mm-conveyor

while true;
do
  python3 conveyor_control.py 2>&1 | vlog --date --name=/var/lib/cloud9/vention-control/machineMotion/logs/conveyor-server ;
done
