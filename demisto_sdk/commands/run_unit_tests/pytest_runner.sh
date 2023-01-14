#!/bin/sh
set -e

echo "Running tests..."

python -m pip install --no-cache-dir -q pytest pytest-mock requests-mock pytest-asyncio pytest-xdist pytest-datadir-ng freezegun pytest-cov 
pytest . -v --junitxml=.report_pytest.xml --cov --cov-report=xml