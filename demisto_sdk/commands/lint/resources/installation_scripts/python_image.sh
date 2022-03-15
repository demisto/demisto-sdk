#!/bin/sh
mkdir -p /devwork/
cd /devwork
chown -R :4000 /devwork/
chmod -R 775 /devwork
OS_RELEASE=$(cat /etc/os-release); if echo "$OS_RELEASE" | grep -q "alpine"; \
then apk add --no-cache --virtual .build-deps python3-dev gcc build-base; \
elif echo "$OS_RELEASE" | grep -qi "Debian"; \
then apt-get update && apt-get install -y --no-install-recommends gcc python3-dev;fi; \
pip install --no-cache-dir -r /test-requirements.txt; \
if echo "$OS_RELEASE" | grep -q "alpine"; then apk del .build-deps; \
elif echo "$OS_RELEASE" | grep -qi "Debian"; \
then apt-get purge -y --auto-remove gcc python3-dev; fi;
