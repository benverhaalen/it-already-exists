# Build context must contain only reviewed SDK compiler dependencies in sdk/.
# Pin BASE_IMAGE to the reviewed linux/amd64 Node 22 Debian image digest.
ARG BASE_IMAGE=node@sha256:43ac6c60b8f89723f746e8a92ce91abd5017e627ce1ddfe4238355d3a30b772c
FROM ${BASE_IMAGE}
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jdk-headless python3 zip unzip \
 && rm -rf /var/lib/apt/lists/*
COPY sdk/ /opt/android-sdk/
ENV ANDROID_HOME=/opt/android-sdk
ENV PATH=/opt/android-sdk/build-tools/35.0.0:${PATH}
# Qualification checks execute separately with the production boundary settings.
WORKDIR /work
