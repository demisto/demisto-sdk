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

INSTALL_SUCCESS=0
pip config set global.disable-pip-version-check true

pip install --no-cache-dir --progress-bar off -r /test-requirements.txt || INSTALL_SUCCESS=1

# if installation fails, we need to install gcc to compile
if [ "$INSTALL_SUCCESS" -eq 1 ]
then
    if [ "$ID" = "alpine" ]
    then
        apk update && apk add --no-cache --virtual .build-deps python3-dev gcc build-base;
    elif [ "$ID" = "debian" ]
    then
        apt-get update && apt-get install -y --no-install-recommends gcc python3-dev
    fi
    pip install --no-cache-dir --progress-bar off -r /test-requirements.txt
    if [ "$ID" = "alpine" ]
    then
        # Cleanup
        apk del .build-deps || true
    elif [ "$ID" = "debian" ]
    then
        apt-get purge -y --auto-remove gcc python3-dev
    fi
    pip freeze
fi


unset REQUESTS_CA_BUNDLE
