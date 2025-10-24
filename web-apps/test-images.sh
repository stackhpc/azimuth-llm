#!/bin/bash
set -e

IMAGE_TAG="${1:-latest}"
echo Testing image tag $IMAGE_TAG

find_images() {
    images=""
    for dir in $(ls $1); do
        if [[ -f $1/$dir/Dockerfile ]]; then
            images+="$dir "
        fi
    done
    echo $images
}

image_name() {
    echo ghcr.io/stackhpc/azimuth-llm-$1-ui
}

build() {
    if [[ -f $1/Dockerfile ]]; then
        echo Building $1 docker image
        docker build . -t $(image_name $1) -f $1/Dockerfile
    else
        echo No Dockerfile found for $1
        exit 1
    fi
}

log () {
    echo
    echo $@
}

test() {

    echo
    echo "----- Starting test process for $1 app -----"
    echo

    if [[ -f $1/test.py ]]; then

        DOCKER_NET_NAME=host

        # DOCKER_NET_NAME=azimuth-llm-shared
        # if [[ ! $(docker network ls | grep $DOCKER_NET_NAME) ]]; then
        #     docker network create $DOCKER_NET_NAME
        # fi

        # Ensure app image is available
        IMAGE=$(image_name $1):$IMAGE_TAG
        if [[ $IMAGE_TAG == "latest" ]]; then
            build $1
        else
            log "Pulling image $IMAGE"
            docker pull $IMAGE
        fi

        # Ensure Ollama instance is available
        if [[ $(curl -s localhost:11434) != "Ollama is running" ]]; then
            log "Ollama not running on localhost:11434 - aborting test"
            exit 1
            # log "Using existing ollama process running on localhost:11434"
        # else
        #     log "Ollama process not running - starting containerised server"
        #     docker run --rm --network $DOCKER_NET_NAME -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
        #     sleep 3
        #     docker exec ollama ollama pull smollm2:135m
        fi

        log "Starting Gradio app container"
        docker run --network $DOCKER_NET_NAME -d --name $1-app $IMAGE

        # Give the app time to start
        sleep 10

        log "Running tests"
        # docker run --network $DOCKER_NET_NAME --rm \
        #     --name $1-test-suite \
        #     -e GRADIO_URL=http://$1-app:7860 --entrypoint python \
        #     $IMAGE \
        #     test.py
        docker run --network $DOCKER_NET_NAME --rm \
            --name $1-test-suite \
            --entrypoint python \
            $IMAGE \
            test.py

        log "Removing containers:"
        # docker rm -f ollama $1-app
        docker rm -f $1-app

        # log "Removing docker network:"
        # docker network rm $DOCKER_NET_NAME

        echo
        echo "----- Tests succeed -----"
        echo
    else
        echo No test.py file found for $1 app
    fi
}

for image in $(find_images .); do
    test $image
done
