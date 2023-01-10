#!/bin/sh
echo "Running pre-commit hooks"
set -e

name=$1
content_path=$2
image=$3
relative_path=$4
# generate a random string to use as a container name

docker rm -f "$name" || true
docker build --build-arg IMAGENAME=$image -t "$name" .
docker run --rm -v "$content_path":/content -w /content/$relative_path $name pytest .
echo "DONE"