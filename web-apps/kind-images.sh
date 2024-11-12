set -e

source functions.sh

if [[ -z $1 ]]; then
    echo "Published image tag must be provided as sole command line arg"
    exit 1
fi

# Clean up some storage capacity in CI runner
if [[ $CI == "true" ]]; then
    # Debug storage issues
    set -x
    docker system df
    docker system prune -af
    docker system df
    lsblk
    df -h
    set +x
fi


REMOTE_TAG=$1
CLUSTER_NAME=${2:-kind}
echo Kind cluster name: $CLUSTER_NAME
KIND_TAG=local
for image in $(find_images .); do
    full_name=ghcr.io/stackhpc/azimuth-llm-$image-ui
    echo $full_name:{$REMOTE_TAG,$KIND_TAG}
    docker pull $full_name:$REMOTE_TAG
    docker image tag $full_name:$REMOTE_TAG $full_name:$KIND_TAG
    # NOTE(scott): The 'load docker-image' command saves the
    # intermediate tar archive to /tmp which has limited space
    # inside a GH runner so do each step manually here instead.
    # kind load docker-image -n $CLUSTER_NAME $full_name:$KIND_TAG
    # Apparently there's a separate 75G disk at /mnt so try using it.
    if [[ $CI == "true" ]]; then
        DIR=/mnt/gimme-more-space
        sudo mkdir $DIR
        sudo chown -R $USER:$USER $DIR
        TAR_PATH=$DIR/image.tar
    else
        TAR_PATH="./image.tar"
    fi
    docker image save -o $TAR_PATH $full_name:$KIND_TAG
    docker rm $full_name:{$REMOTE_TAG,$KIND_TAG}
    kind load image-archive -n $CLUSTER_NAME $TAR_PATH
    rm image.tar
done
