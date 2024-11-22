#!/bin/sh

set -e

if [ "$1" = 'unittest' ]; then
    python3 -m $@
    rm -rf __pycache__
elif [ "$1" = 'bandit' ]; then
    bandit -r .
elif [ "$1" = 'coverage' ]; then
    coverage run -m unittest
    coverage report -m
    rm -rf __pycache__ .coverage
elif [ "$1" = 'production' ]; then
    exec sh -c 'nginx && gunicorn -b 0.0.0.0:8888 app:app'
elif [ -z "$1" ]; then
    exec flask --app app run --debug --host=0.0.0.0
else
    exec "$@"
fi