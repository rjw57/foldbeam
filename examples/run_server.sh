#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR

echo "Starting server... (requires gunicorn)"
echo "After server started, visit file://${SCRIPT_DIR}/leaflet-example.html"
exec gunicorn -b localhost:8080 -w 8 tilestache_provider_server:app

