#!/bin/bash

apt-get update
apt-get install -y zlib1g-dev automake autoconf git \
	libtool subversion libatlas3-base ffmpeg python-pip

pip install .
