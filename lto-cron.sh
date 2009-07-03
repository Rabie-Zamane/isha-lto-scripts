#!/bin/sh

EXIST_HOME=/usr/lib/exist
TIMESTAMP=`date +%Y%m%d-%H%M%S`
$EXIST_HOME/bin/backup.sh -d /home/kevala/tsbackup/$TIMESTAMP -u admin -p admin -b /db -ouri=xmldb:exist://
