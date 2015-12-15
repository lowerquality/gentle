#!/bin/bash

# Prepare Kaldi
cd ext/kaldi/tools
make atlas openfst OPENFST_VERSION=1.4.1
cd ../src
./configure --static --static-math=yes --static-fst=yes --use-cuda=no
make depend
cd ../../
