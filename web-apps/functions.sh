#!/bin/bash

find_images() {
    images=""
    for dir in $(ls $1); do
        if [[ -f $1/$dir/Dockerfile ]]; then
            images+="$dir "
        fi
    done
    echo $images
}

build() {
    if [[ -f $1/Dockerfile ]]; then
        echo Building $1 docker image
        docker build . -t ghcr.io/stackhpc/azimuth-llm-$1-ui -f $1/Dockerfile
    else
        echo No Dockerfile found for $1
    fi
}
