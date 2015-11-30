#!/bin/bash

# Prepare Kaldi
cd ext/kaldi/tools
make atlas openfst
cd ../src
./configure --static --static-math=yes --static-fst=yes --use-cuda=no
make depend
cd ../../
