#!/bin/sh

set -e
python3 manage.py migrate --no-input
python3 manage.py collectstatic --no-input
gunicorn ClinicBALUEV.wsgi -b 0.0.0.0:8000 -w 2
exec "$@"
