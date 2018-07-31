#!/bin/bash

set -e

git submodule init
git submodule update

./install_deps.sh
pushd ext
./install_kaldi.sh
popd
./install_models.sh
pushd ext
make depend
make
popd
