import os

from util.paths import get_resource
from gentle import metasentence

class Resources():

    def __init__(self):
        self.proto_langdir = get_resource('PROTO_LANGDIR')
        self.nnet_gpu_path = get_resource('data/nnet_a_gpu_online')
        self.full_hclg_path = get_resource('data/graph/HCLG.fst')
        with open(os.path.join(self.proto_langdir, "graphdir/words.txt")) as fh:
            self.vocab = metasentence.load_vocabulary(fh)
