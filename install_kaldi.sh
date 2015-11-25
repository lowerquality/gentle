#!/bin/bash

# Prepare Kaldi
cd kaldi/tools
make # -j 8
cd ../src
./configure --static --static-math=yes --static-fst=yes --use-cuda=no
make depend # -j 8
cd ../../
