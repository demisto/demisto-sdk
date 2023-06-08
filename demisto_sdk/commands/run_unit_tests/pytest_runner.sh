#!/bin/sh
set -e

echo "Running tests..."
python -m pytest . -c /content/Tests/scripts/dev_envs/pytest -v --rootdir=/content --junitxml=.report_pytest.xml --cov-report= --cov=.
