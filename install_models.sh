#!/bin/bash

set -e

# Download models
wget http://lowerquality.com/gentle/kaldi-models-0.02.zip
unzip kaldi-models-0.02.zip

# Update nnet model config files
cd data
for x in nnet_a_gpu_online/conf/*conf; do
    cp $x $x.orig
    sed s:/Users/rmo/data/speech-data/:$(pwd)/: < $x.orig > $x
done
cd ..
