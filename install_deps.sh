#!/bin/bash

set -e

echo "Installing dependencies..."

# Install OS-specific dependencies
if [[ "$OSTYPE" == "linux-gnu" ]]; then
	apt-get update -qq
	apt-get install -y zlib1g-dev automake autoconf git \
		libtool subversion libatlas3-base python3-pip \
		python3-dev wget unzip python3
	apt-get install -y ffmpeg || echo -n  "\n\nYou have to install ffmpeg from a PPA or from https://ffmpeg.org before you can run gentle\n\n"
	python3 setup.py develop
elif [[ "$OSTYPE" == "darwin"* ]]; then
	brew install ffmpeg libtool automake autoconf wget python3
	sudo python3 setup.py develop
fi
