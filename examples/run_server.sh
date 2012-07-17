#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR

HOST=localhost
PORT=8080

echo "Starting server... (requires gunicorn)"
echo "After server started, visit http://${HOST}:${PORT}/"
exec gunicorn -b "${HOST}:${PORT}" -w 8 tilestache_provider_server:app

