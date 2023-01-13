#!/bin/sh
echo "Running tests..."
echo $GITHUB_ACTIONS
echo $PYTEST_RUN_PATH
set -e
python -m pip install --no-cache-dir -q pytest pytest-mock requests-mock pytest-asyncio pytest-xdist pytest-datadir-ng freezegun pytest-json pytest-cov pytest-github-actions-annotate-failures
pytest . -v