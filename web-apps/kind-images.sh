set -e

source functions.sh

if [[ -z $1 ]]; then
    echo "Published image tag must be provided as sole command line arg"
    exit 1
fi

REMOTE_TAG=$1
CLUSTER_NAME=${2:-kind}
echo Kind cluster name: $CLUSTER_NAME
KIND_TAG=local
for image in $(find_images .); do
    full_name=ghcr.io/stackhpc/azimuth-llm-$image-ui
    echo $full_name
    docker pull $full_name:$REMOTE_TAG
    docker image tag $full_name:$REMOTE_TAG $full_name:$KIND_TAG
    # NOTE(scott): The 'load docker-image' command saves the
    # intermediate tar archive to /tmp which has limited space
    # inside a GH runner so do each step manually here instead.
    # kind load docker-image -n $CLUSTER_NAME $full_name:$KIND_TAG
    docker image save -o ./image.tar $full_name:$KIND_TAG
    kind load image-archive -n $CLUSTER_NAME ./image.tar
    rm image.tar
done
