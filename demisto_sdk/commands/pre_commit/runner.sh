#!/bin/sh
echo "Running tests..."
set -e
python -m pip install --no-cache-dir -q pytest pytest-mock requests-mock pytest-asyncio pytest-xdist pytest-datadir-ng freezegun pytest-json pytest-cov pytest-github-actions-annotate-failures
pytest . -v --json=pytest_report.json