#!/bin/bash

set -e

echo "Installing dependencies..."

# Install OS-specific dependencies
if [[ "$OSTYPE" == "linux-gnu" ]]; then
	apt-get update -qq
	apt-get install -y zlib1g-dev automake autoconf git \
		libtool subversion libatlas3-base python-pip \
		python-dev wget unzip
	apt-get install -y ffmpeg || echo -n  "\n\nYou have to install ffmpeg from a PPA or from https://ffmpeg.org before you can run gentle\n\n"
	pip install .
elif [[ "$OSTYPE" == "darwin"* ]]; then
	brew install ffmpeg libtool automake autoconf wget

	sudo easy_install pip
	sudo pip install .
fi
