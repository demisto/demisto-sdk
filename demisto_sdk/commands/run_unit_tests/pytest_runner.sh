#!/bin/sh
set -e

echo "Running tests..."
python -m pytest . -v --rootdir=/content --junitxml=.report_pytest.xml --cov-report= --cov=.
