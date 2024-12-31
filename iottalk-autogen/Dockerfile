FROM python:3.7.10-slim

WORKDIR /iottalk-autogen

COPY . /iottalk-autogen

RUN apt update && \
# Install build dependencies
    apt install -y --no-install-recommends git python3-dev default-libmysqlclient-dev build-essential && \
    pip install --no-cache-dir -U pip && \
# Install requirements
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r production-requirements.txt && \
# Remove build dependencies, unused packages and the packages index
# Ref: https://unix.stackexchange.com/questions/217369/clear-apt-get-list
    apt autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
# Create lag path
    mkdir -p /log/autogen && \
    mkdir -p /log/device && \
    mkdir -p /log/edutalk 
