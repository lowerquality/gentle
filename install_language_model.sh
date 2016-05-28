wget -c http://kaldi-asr.org/downloads/build/2/sandbox/online/egs/fisher_english/s5/exp/tri5a/graph/archive.tar.gz
tar -xzvf archive.tar.gz ./HCLG.fst
mkdir -p data/graph
mv HCLG.fst data/graph/
