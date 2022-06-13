#!/bin/sh
set -e
if [ -f '/etc/ssl/certs/ca-certificates.crt' ]
then
    set REQUESTS_CA_BUNDLE='/etc/ssl/certs/ca-certificates.crt'
fi
mkdir -p /devwork/
cd /devwork
chown -R :4000 /devwork/
chmod -R 775 /devwork
. /etc/os-release
if [ "$ID" = "alpine" ]
then
    apk add --no-cache --virtual .build-deps python3-dev gcc build-base;
elif [ "$ID" = "debian" ]
then
    apt-get update && apt-get install -y --no-install-recommends gcc python3-dev
fi
pip install --no-cache-dir -r /test-requirements.txt
if [ "$ID" = "alpine" ]
then
    apk del .build-deps
elif [ "$ID" = "debian" ]
then
    apt-get purge -y --auto-remove gcc python3-dev
fi
pip freeze
unset REQUESTS_CA_BUNDLE
