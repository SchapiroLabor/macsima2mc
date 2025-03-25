# Use the official micromamba image as a base
FROM mambaorg/micromamba:latest
LABEL maintainer="Victor Perez"

# Set the base layer for micromamba and copy the environment file
COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/env.yaml

RUN apt-get update -qq && apt-get install -y \
    build-essential \
    ffmpeg \
    libsm6 \
    libxext6 \
    procps

RUN micromamba install -y -n base -f /tmp/env.yaml && \
    micromamba clean --all --yes

ENV PATH="${PATH}:/opt/conda/bin"

WORKDIR /staging

COPY . .
# Update package manager and install essential build tools procps is required for Nextflow/nf-core



