FROM python:slim

RUN apt-get update && apt install git gcc nodejs npm -y && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir demisto-sdk

WORKDIR /content


RUN npm install -g @mdx-js/mdx fs-extra commander

CMD python3 -m demisto_sdk --help