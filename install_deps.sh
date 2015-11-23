#!/bin/bash

set -e

echo "Installing dependencies..."

# Install OS-specific dependencies
if [[ "$OSTYPE" == "linux-gnu" ]]; then
	apt-get update
	apt-get install -y zlib1g-dev automake autoconf git \
		libtool subversion libatlas3-base ffmpeg python-pip \
		python-dev wget unzip

	pip install .
elif [[ "$OSTYPE" == "darwin"* ]]; then
	brew install ffmpeg libtool automake autoconf wget

	sudo easy_install pip
	sudo pip install .
fi
