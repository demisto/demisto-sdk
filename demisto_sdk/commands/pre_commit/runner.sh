#!/bin/sh
echo "Running tests..."
set -e
python -m pip install --no-cache-dir -q pytest pytest-mock requests-mock pytest-asyncio pytest-xdist pytest-datadir-ng freezegun pytest-json-report pytest-cov 
pytest . -v --json-report