#!/bin/bash

set -e

VERSION="0.03"

download_models() {
	local version="$1"
	local filename="kaldi-models-$version.zip"
	local url="https://lowerquality.com/gentle/$filename"
	wget -O $filename $url
	unzip $filename
	rm $filename
}

echo "Downloading models for v$VERSION..." 1>&2
download_models $VERSION
