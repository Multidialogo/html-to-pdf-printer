#!/bin/sh

set -e

safe_cleanup() {
    # Do not fail the whole command if mounted files are not writable.
    rm -rf "$@" 2>/dev/null || true
}

if [ "$1" = 'unittest' ]; then
    python3 -m "$@"
    safe_cleanup __pycache__
elif [ "$1" = 'bandit' ]; then
    bandit -r .
elif [ "$1" = 'coverage' ]; then
    coverage run -m unittest
    coverage report -m
    safe_cleanup __pycache__ .coverage
elif [ "$1" = 'production' ]; then
    exec sh -c 'nginx && gunicorn -b 0.0.0.0:8888 app:app'
elif [ -z "$1" ]; then
    exec flask --app app run --debug --host=0.0.0.0
else
    exec "$@"
fi