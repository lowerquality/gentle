#!/bin/bash

set -e
set -x

echo "Installing dependencies..."

# Install OS-specific dependencies
if [[ "$OSTYPE" == "darwin"* ]]; then
	brew install ffmpeg libtool automake autoconf wget python3

	sudo easy_install pip
	sudo pip install .
elif [[ "$OSTYPE" == "linux-gnu" ]]; then
	ID=$(awk -F= '/^ID=/{gsub(/"/, "", $2); print $2}' /etc/os-release)
	if [[ "$ID" == "ubuntu" ]]; then
		if [ -f /.dockerenv ]; then
			SUDO=
		else
			SUDO=sudo
		fi
		$SUDO apt-get update -qq
		$SUDO apt-get install -y zlib1g-dev automake autoconf git \
			libtool subversion libatlas3-base python-pip \
			python-dev wget unzip gfortran python3
		$SUDO apt-get install -y ffmpeg || echo -n  "\n\nYou have to install ffmpeg from a PPA or from https://ffmpeg.org before you can run gentle\n\n"
		$SUDO pip install -e .
	elif [[ "$ID" == "centos" ]]; then
		sudo yum check-update
		sudo yum install -y zlib1g-dev automake autoconf git \
			libtool subversion libatlas3-base python-pip \
			python-dev wget unzip gcc-gfortran python34 python34-pip
		sudo yum install -y ffmpeg || echo -n  "\n\nYou have to install ffmpeg from a PPA or from https://ffmpeg.org before you can run gentle\n\n"
		sudo pip install -e .    # NOT pip3 !!
	fi
fi
