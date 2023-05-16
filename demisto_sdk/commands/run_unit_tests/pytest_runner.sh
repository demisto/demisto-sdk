#!/bin/sh
set -e

echo "Running tests..."
output=$(python --version 2>&1)
echo "Python version: $output"

if echo "$output" | grep -q "Python 3"; then
    additional_dependencies="pytest pytest-mock requests-mock pytest-xdist pytest-datadir-ng freezegun pytest-cov hypothesis pytest-asyncio"
else
    additional_dependencies="pytest pytest-mock requests-mock pytest-xdist pytest-datadir-ng freezegun pytest-cov hypothesis"
fi
python -m pip install --no-cache-dir -q $additional_dependencies
python -m pytest . -v --rootdir=/content --junitxml=.report_pytest.xml --cov-report= --cov=.
