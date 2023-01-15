ARG IMAGENAME


FROM --platform=amd64 ${IMAGENAME}

ENV PYTHONPATH /content/Packs/Base/Scripts/CommonServerPython/:/content/Packs/Base/Scripts/CommonServerUserPython/:/content/Tests/demistomock/


RUN python -m pip install --no-cache-dir pytest pytest-mock requests-mock pytest-asyncio pytest-xdist pytest-datadir-ng freezegun pytest-json pytest-cov
