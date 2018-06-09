import logging
import os

from .util.paths import get_resource, ENV_VAR
from . import metasentence

class Resources():

    def __init__(self):
        self.proto_langdir = get_resource('exp')
        self.nnet_gpu_path = get_resource('exp/tdnn_7b_chain_online/')
        self.full_hclg_path = get_resource('exp/tdnn_7b_chain_online/graph_pp/HCLG.fst')

        def require_dir(path):
            if not os.path.isdir(path):
                raise RuntimeError("No resource directory %s.  Check %s environment variable?" % (path, ENV_VAR))


        require_dir(self.proto_langdir)
        require_dir(self.nnet_gpu_path)

        with open(os.path.join(self.proto_langdir, "langdir", "words.txt")) as fh:
            self.vocab = metasentence.load_vocabulary(fh)


