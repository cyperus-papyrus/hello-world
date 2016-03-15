#!/bin/bash
# ВМЕСТО flock
HOMEDIR=/home/helga/olgavr/marcapp
PROGNAME=create_marc
PID=$HOMEDIR/$PROGNAME.pid
################################################################################
# Контроль двойного запуска программы
. $PID 2>/dev/null
PRC=`/bin/ps -p $MYPID 2>/dev/null|/bin/grep -v PID 2>/dev/null`
if [ "$PRC" != "" ]; then
    echo "Process already running."
    exit 3
fi
echo "MYPID=$$" > $PID 2>/dev/null
################################################################################

cd $HOMEDIR
/home/helga/olgavr/venv/bin/python2.7 $HOMEDIR/$PROGNAME.py > $PROGNAME.log 2>&1
sleep 1
rm -f $PID 2>/dev/null
################################################################################
exit 0