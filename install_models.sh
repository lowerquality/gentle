#!/bin/bash

set -e

VERSION="0.03"

download_models() {
	local version="$1"
	local filename="gentle_aligner_models_$version.zip"
	local url="https://s3-us-west-2.amazonaws.com/descript-public/app-models/$filename"
	curl -O $url
	unzip $filename
        rm $filename
}

echo "Downloading models for v$VERSION..." 1>&2
download_models $VERSION
