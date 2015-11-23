#!/bin/bash

# Install OS-specific dependencies
if [[ "$OSTYPE" == "linux-gnu" ]]; then
	sh dependencies_ubuntu.sh
elif [[ "$OSTYPE" == "darwin"* ]]; then
    sh dependencies_osx.sh
fi

# Build Kaldi
cd kaldi/tools
make # -j 8
cd ../src
./configure --static --static-math=yes --static-fst=yes --use-cuda=no
make depend # -j 8
cd ../../

# Build "standard_kaldi" python wrapper
make

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
