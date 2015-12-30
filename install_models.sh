#!/bin/bash

set -e

VERSION="0.02"

download_models() {
	local version="$1"
	local filename="kaldi-models-$version.zip"
	local url="http://lowerquality.com/gentle/$filename"
	wget -O $filename $url
	unzip $filename
}

echo "Downloading models for v$VERSION..." 1>&2
download_models $VERSION
