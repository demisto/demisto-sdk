#!/bin/sh

set -e

name=$0
image=$1
path=$2

docker build --build-arg $image -t $name .
docker run --rm -v $path:/devwork -w /devwork pytest .
