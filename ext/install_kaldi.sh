#!/bin/bash

# Prepare Kaldi
pushd kaldi/tools
make
./extras/install_openblas.sh
popd
pushd kaldi/src
./configure --static --static-math=yes --static-fst=yes --use-cuda=no --openblas-root=../tools/OpenBLAS/install
make -j4 depend
make -j4
popd

