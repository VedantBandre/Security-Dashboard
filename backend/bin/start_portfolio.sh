#!/bin/sh
set -eu
python manage.py release_portfolio
exec gunicorn --config gunicorn.conf.py config.wsgi:application
