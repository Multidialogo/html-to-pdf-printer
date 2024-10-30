#!/bin/sh

if [ "$1" = "unittest" ]; then
    python -m $@
elif [ "$1" = "bandit" ]; then
    bandit -r .
elif [ "$1" = "coverage" ]; then
    coverage run -m unittest
    coverage report -m
else
    exec /lambda-entrypoint.sh $@
fi