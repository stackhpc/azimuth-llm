FROM ghcr.io/astral-sh/uv:python3.11-trixie

ARG IMAGEMAGICK_VERSION=8:7.1.1.43+dfsg1-1+deb13u11
ARG LIBUNBOUND_VERSION=1.22.0-2+deb13u3
ARG KRB5_VERSION=1.21.3-5+deb13u1
ARG LIBGCRYPT_VERSION=1.11.0-7+deb13u1
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libsm6 \
        libxext6 \
        "imagemagick=${IMAGEMAGICK_VERSION}" \
        "imagemagick-7-common=${IMAGEMAGICK_VERSION}" \
        "imagemagick-7.q16=${IMAGEMAGICK_VERSION}" \
        "libmagickcore-7-arch-config=${IMAGEMAGICK_VERSION}" \
        "libmagickcore-7-headers=${IMAGEMAGICK_VERSION}" \
        "libmagickcore-7.q16-10=${IMAGEMAGICK_VERSION}" \
        "libmagickcore-7.q16-10-extra=${IMAGEMAGICK_VERSION}" \
        "libmagickcore-7.q16-dev=${IMAGEMAGICK_VERSION}" \
        "libmagickcore-dev=${IMAGEMAGICK_VERSION}" \
        "libmagickwand-7-headers=${IMAGEMAGICK_VERSION}" \
        "libmagickwand-7.q16-10=${IMAGEMAGICK_VERSION}" \
        "libmagickwand-7.q16-dev=${IMAGEMAGICK_VERSION}" \
        "libmagickwand-dev=${IMAGEMAGICK_VERSION}" \
        "libunbound8=${LIBUNBOUND_VERSION}" \
        "krb5-multidev=${KRB5_VERSION}" \
        "libgssapi-krb5-2=${KRB5_VERSION}" \
        "libgssrpc4t64=${KRB5_VERSION}" \
        "libk5crypto3=${KRB5_VERSION}" \
        "libkadm5clnt-mit12=${KRB5_VERSION}" \
        "libkadm5srv-mit12=${KRB5_VERSION}" \
        "libkdb5-10t64=${KRB5_VERSION}" \
        "libkrb5-3=${KRB5_VERSION}" \
        "libkrb5-dev=${KRB5_VERSION}" \
        "libkrb5support0=${KRB5_VERSION}" \
        "libgcrypt20=${LIBGCRYPT_VERSION}" && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


ARG DIR=flux-image-gen

RUN uv pip install --system --no-cache-dir --upgrade \
        pip \
        setuptools \
        wheel

COPY $DIR/requirements.txt requirements.txt
RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY purge-google-fonts.sh .
RUN bash purge-google-fonts.sh

WORKDIR /app

COPY $DIR/*.py .

COPY $DIR/gradio_config.yaml .

COPY $DIR/test-image.jpg .

ENTRYPOINT ["fastapi", "run", "api_server.py"]
