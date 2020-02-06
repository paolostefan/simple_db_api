#!/bin/bash
### BEGIN INIT INFO
# Provides:          simple_db_api.sh
# Required-Start:    mysql
# Required-Stop:     
# Should-Start:      
# Should-Stop:       
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Simple DB API webserver
# Description:       Expose a read-only database API on the web.
### END INIT INFO

BASE_DIR=/usr/src/simple_db_api
LOG_FILE=/var/log/simple_db_api.log
PID_FILE=/var/run/simple_db_api.pid

case "$1" in
start)
        echo "Starting Simple Database API..."
        if [ -f ${PID_FILE} ]; then
          echo "Pid file found - unclean shutdown?"
        fi
        ${BASE_DIR}/venv/bin/python3 ${BASE_DIR}/server.py >>${LOG_FILE} 2>&1 &
        echo $! > ${PID_FILE}
        echo "Started Simple Database API, pid = $!"
        ;;
stop)
        echo "Stopping Simple Database API..."
        if [ ! -f ${PID_FILE} ]; then
          echo "Pid file not found - shutdown not needed"
        else
          kill "$(cat "${PID_FILE}")"
          rm ${PID_FILE}
        fi
        ;;
restart)
        $0 stop
        $0 start
        ;;
reload|force-reload) echo "Not implemented yet"
        ;;
*)      echo "Usage: $0 {start|stop|restart|reload|force-reload}"
        exit 2
        ;;
esac
exit 0