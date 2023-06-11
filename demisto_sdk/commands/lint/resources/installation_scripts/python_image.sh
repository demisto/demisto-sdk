#!/bin/sh
set -e
# if [ -f '/etc/ssl/certs/ca-certificates.crt' ]
# then
#     set REQUESTS_CA_BUNDLE='/etc/ssl/certs/ca-certificates.crt'
# fi
CONNECT_SERVER="github.com:443"

FILE=/etc/ssl/certs/certs.crt

REGEX_BEGIN="/^-----BEGIN CERTIFICATE-----$/"
REGEX_END="/^-----END CERTIFICATE-----$"
openssl s_client -showcerts -connect $CONNECT_SERVER | \
    sed -n "$REGEX_BEGIN,$REGEX_END/p" > "$FILE"
update-ca-certificates
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
pip install --no-cache-dir --progress-bar off -r /test-requirements.txt
if [ "$ID" = "alpine" ]
then
    apk del .build-deps
elif [ "$ID" = "debian" ]
then
    apt-get purge -y --auto-remove gcc python3-dev
fi
pip freeze
unset REQUESTS_CA_BUNDLE
