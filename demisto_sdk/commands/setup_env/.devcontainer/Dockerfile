ARG IMAGENAME

FROM --platform=linux/amd64 ${IMAGENAME}

ADD createCerts.sh /

RUN chmod +x /createCerts.sh \
    && /createCerts.sh /usr/local/share/ca-certificates/certs.crt \
    && update-ca-certificates \
    && apk update || apt-get update -y || echo "Could not update package mangaer" \
    && apk add bash || echo "No alpine, no need to install bash" \
    && apk add git || apt-get install git -y || echo "Could not install git" \
    && apk add build-base || apt-get install build-essential -y || echo "Could not install build-essential" \
    # check if pip command exists
    && if [ -x "$(command -v pip)" ]; then \
        pip install autopep8 flake8 || echo "Could not install autopep8 or flake8"; \
        if [ $(python -c 'import sys; print(sys.version_info[0])') == "3" ]; then \
            # mypy supports only py3
            pip install mypy types-dateparser types-requests || echo "Could not install mypy"; \
        fi \
    fi \
    && git config --system --add safe.directory /workspaces/content

ENV NODE_EXTRA_CA_CERTS /usr/local/share/ca-certificates/certs.crt
