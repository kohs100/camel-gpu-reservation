FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN sed -i \
  's#http://archive.ubuntu.com#http://mirror.kakao.com#g' \
  /etc/apt/sources.list

RUN apt-get update -y && \
    apt-get install -y \
      apt-transport-https \
      ca-certificates \
      gnupg \
      python3 \
      python3-pip \
      python3-dev \
      git \
      nano \
      curl \
      wget \
      ssh

# Add NVIDIA package repositories
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb
RUN dpkg -i cuda-keyring_1.0-1_all.deb
RUN apt-get update

# Install Nsight Compute (adjust version as needed)
RUN apt-get install -y nsight-compute-2025.3.0

