from queue import Queue
from gentle import standard_kaldi

def build(resources, nthreads=4, hclg_path=None, kaldi_module=None):
    if hclg_path is None: hclg_path = resources.full_hclg_path
    if kaldi_module is None: kaldi_module = standard_kaldi

    kaldi_queue = Queue()
    for i in range(nthreads):
        kaldi_queue.put(kaldi_module.Kaldi(
            resources.nnet_gpu_path,
            hclg_path,
            resources.proto_langdir)
        )
    return kaldi_queue
