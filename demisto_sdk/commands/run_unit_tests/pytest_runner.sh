#!/bin/sh
set -e

echo "Running tests..."

python -m pip install --no-cache-dir -q pytest pytest-mock requests-mock pytest-asyncio pytest-xdist pytest-datadir-ng freezegun pytest-json-report pytest-cov 
pytest . -v --json-report