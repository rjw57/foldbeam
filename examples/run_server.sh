#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR

if [ -z "${SERVEHOST}" ]; then
    SERVEHOST=localhost
fi

if [ -z "${SERVEPORT}" ]; then
    SERVEPORT=8080
fi

echo "Starting server... (requires gunicorn)"
echo "After server started, visit http://${SERVEHOST}:${SERVEPORT}/"
exec gunicorn -b "${SERVEHOST}:${SERVEPORT}" -w 8 tilestache_provider_server:app

