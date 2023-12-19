# Use Ubuntu 22.04 LTS (Jammy Jellyfish) as the base image
FROM ubuntu:22.04

# Set environment variable to avoid messages during package installation
ARG DEBIAN_FRONTEND=noninteractive

# Update and install packages
RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y --no-install-recommends \
    build-essential \
    software-properties-common \
    byobu \
    curl \
    git \
    htop \
    man \
    unzip \
    vim \
    wget \
    python3 \
    net-tools \
    iputils-ping && \
    # Clean up
    rm -rf /var/lib/apt/lists/*

# Set the working directory to /root
WORKDIR /root

# Copy all files from the current directory to the container
COPY . .

# Make the script executable
RUN chmod +x /root/objects/generateobjects.sh

# Define default command to start the bash shell
CMD ["bash"]
