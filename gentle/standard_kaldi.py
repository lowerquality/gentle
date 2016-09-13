'''Glue code for communicating with standard_kaldi C++ process'''
import json
import logging
import os
import subprocess
import tempfile
import wave

from gentle import ffmpeg
from util.paths import get_binary
from gentle.rpc import RPCProtocol
from gentle.resources import Resources

EXECUTABLE_PATH = get_binary("ext/standard_kaldi")

class Kaldi(object):
    '''Kaldi spawns a standard_kaldi subprocess and provides a
    Python wrapper for communicating with it.'''
    def __init__(self, nnet_dir, hclg_path, proto_langdir):
        self.proto_langdir = proto_langdir
        devnull = open(os.devnull, 'w')
        cmd = [EXECUTABLE_PATH, nnet_dir, hclg_path, proto_langdir]
        self._subprocess = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=devnull)

        self._transitions = None
        self._words = None
        self._stopped = False

        self.rpc = RPCProtocol(self._subprocess.stdin, self._subprocess.stdout)

    def push_chunk(self, buf):
        '''Push a chunk of audio. Returns true if it worked OK.'''
        self.rpc.do('push-chunk', body=buf)

    def get_partial(self):
        '''Dump the provisional (non-word-aligned) transcript'''
        body, _ = self.rpc.do('get-partial')
        hypothesis = json.loads(body)['hypothesis']
        words = [h['word'] for h in hypothesis]
        return " ".join(words)

    def get_final(self):
        '''Dump the final, phone-aligned transcript'''
        body, _ = self.rpc.do('get-final')
        hypothesis = json.loads(body)['hypothesis']
        return hypothesis

    def reset(self):
        '''Reset the decoder, delete the decoding state'''
        self.rpc.do('reset')

    def stop(self):
        '''Quit the program'''
        self.rpc.do('stop')
        self._stopped = True

def main():
    '''Transcribe the given input file using a standard_kaldi C++ subprocess.'''
    import sys

    infile = sys.argv[1]
    outfile = sys.argv[2]

    if len(sys.argv) > 5:
        nnet_dir = sys.argv[3]
        graph_dir = sys.argv[4]
        proto_langdir = sys.argv[5]
        k = Kaldi(nnet_dir, graph_dir, proto_langdir)
    else:
        resources = Resources()
        k = Kaldi(resources.nnet_gpu_path, resources.full_hclg_path, resources.proto_langdir)

    words = None
    for words in k.transcribe_progress(infile, batch_size=1):
        sys.stderr.write(".")
    sys.stderr.write("\n")
    with open(outfile, 'w') as out:
        json.dump(words, out, indent=2)

if __name__ == '__main__':
    main()
