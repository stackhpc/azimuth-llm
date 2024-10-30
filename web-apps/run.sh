#!/bin/bash
set -e

IMAGE_TAG=ghcr.io/stackhpc/azimuth-llm-$1

error() {
    echo $1
    exit 1
}

if [[ -z $1 ]]; then
    error "App name is required as script arg"
elif [[ ! -d $1 ]]; then
    error "App $1 not found"
elif [[ -z $(docker image ls -q $IMAGE_TAG) ]]; then
    ./build.sh $1
else
    echo "Found local $IMAGE_TAG docker image"
fi

docker run --rm -p 7860:7860 $IMAGE_TAG
