#!/bin/bash

# Prepare Kaldi
cd kaldi/tools
make clean
make atlas openfst OPENFST_VERSION=1.4.1
cd ../src
make clean
./configure --static --static-math=yes --static-fst=yes --use-cuda=no
make depend
cd ../../
