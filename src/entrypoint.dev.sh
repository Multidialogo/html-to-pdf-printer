#!/bin/sh

set -e

if [ "$1" = "unittest" ]; then
    python3 -m $@
    rm -rf __pycache__
elif [ "$1" = "bandit" ]; then
    bandit -r .
elif [ "$1" = "coverage" ]; then
    coverage run -m unittest
    coverage report -m
    rm -rf __pycache__ .coverage
else
    exec flask --app app run --debug --host=0.0.0.0
fi