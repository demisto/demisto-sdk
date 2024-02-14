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


pip install --no-cache-dir --progress-bar off -r /test-requirements.txt
pip freeze
unset REQUESTS_CA_BUNDLE
