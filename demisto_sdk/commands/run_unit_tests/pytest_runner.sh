#!/bin/sh
set -e

echo "Running tests..."

python -m pip install --no-cache-dir -q pytest pytest-mock requests-mock pytest-asyncio pytest-xdist pytest-datadir-ng freezegun pytest-cov pytest-pretty
python -m pytest . -v --rootdir=/content --junitxml=.report_pytest.xml --cov-report= --cov=.
