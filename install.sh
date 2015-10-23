# Build Kaldi
cd kaldi/tools
make # -j 8
cd ../src
./configure
make depend # -j 8
make # -j 8
cd ../../

# Build "standard_kaldi" python wrapper
make

# Update nnet model config files
cd data
for x in nnet_a_gpu_online/conf/*conf; do
    cp $x $x.orig
    sed s:/Users/rmo/data/speech-data/:$(pwd)/: < $x.orig > $x
done
cd ..
