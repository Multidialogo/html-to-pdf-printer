#!/bin/sh

if [ "$1" = "unittest" ]; then
    python -m $@
    rm -rf __pycache__
elif [ "$1" = "bandit" ]; then
    bandit -r .
elif [ "$1" = "coverage" ]; then
    coverage run -m unittest
    coverage report -m
    rm -rf __pycache__ .coverage
else
    exec /lambda-entrypoint.sh $@
fi