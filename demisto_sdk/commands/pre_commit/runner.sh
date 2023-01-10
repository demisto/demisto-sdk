#!/bin/sh
echo "Running pre-commit hooks"
set -e
python -m pip install --root-user-action=ignore --no-cache-dir -q pytest pytest-mock requests-mock pytest-asyncio pytest-xdist pytest-datadir-ng freezegun pytest-json pytest-cov
pytest /content/Packs/QRadar/Integrations/QRadar_v3 -v