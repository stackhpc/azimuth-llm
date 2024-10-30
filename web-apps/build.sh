#!/bin/bash
set -e

build() {
    if [[ -f $1/Dockerfile ]]; then
        echo Building $1 docker image
        docker build . -t ghcr.io/stackhpc/azimuth-llm-$1 -f $1/Dockerfile
    else
        echo No Dockerfile found for $1
    fi
}

# If a single app is provided as a
# script arg then just build that image,
# otherwise try building all images.
if [[ ! -z $1 ]]; then
    build $1
else
    for item in $(ls); do
        if [[ -d $item ]]; then
            build $item
        fi
    done
fi
