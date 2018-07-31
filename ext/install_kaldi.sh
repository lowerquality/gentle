#!/bin/bash

# Prepare Kaldi
pushd kaldi/tools
make clean
make atlas openfst OPENFST_VERSION=1.4.1
popd
pushd kaldi/src
./configure --static --static-math=yes --static-fst=yes --use-cuda=no
make clean
make depend
popd
