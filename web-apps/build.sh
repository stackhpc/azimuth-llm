#!/bin/bash
set -e

source functions.sh

# If a single app is provided as a
# script arg then just build that image,
# otherwise try building all images.
if [[ ! -z $1 ]]; then
    build $1
else
    for image in $(find_images .); do
        build $image
    done
fi
