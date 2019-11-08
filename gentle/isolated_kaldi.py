import subprocess
import os
import logging
import sys
import uuid

from .util.paths import get_binary

EXECUTABLE_PATH = get_binary("ext/k3")

logger = logging.getLogger(__name__)

class Kaldi:
    def __init__(self, nnet_dir=None, hclg_path=None, suppress_stderr=False):
        self.k3_id = str(uuid.uuid4())[0:6]
        self.finished = False
        self.cmd = [EXECUTABLE_PATH]
        self.result = None

        if nnet_dir is not None:
            self.cmd.append(nnet_dir)
            self.cmd.append(hclg_path)

        if not os.path.exists(hclg_path):
            logger.error('hclg_path does not exist: %s', hclg_path)

    def __build_command(self, buffer):
        return (
            'push-chunk\n'.encode() +
            f'{int(len(buffer)/2)}\n'.encode() +
            buffer +
            'get-final\n'.encode() +
            'reset\n'.encode() +
            'stop\n'.encode()
        )

    def push_chunk(self, buf):
        logger.debug("%s Processing buffer of size %i", self.k3_id, len(buf))
        result = subprocess.run(self.cmd, capture_output=True, input=self.__build_command(buf))
        lines = [x.strip() for x in result.stdout.decode().split('\n') if len(x.strip()) > 0]

        if result.returncode != 0 or len(lines) < 2 or not lines[0].startswith('ok'):
            return

        words = []

        for line in lines[1:]:
            logger.debug("%s Reading from k3 %s", self.k3_id, line)

            if line.startswith('done'):
                break

            parts = line.split(' / ')

            if line.startswith('word'):
                word = {}
                word['word'] = parts[0].split(': ')[1]
                word['start'] = float(parts[1].split(': ')[1])
                word['duration'] = float(parts[2].split(': ')[1])
                word['phones'] = []
                words.append(word)
            elif line.startswith('phone'):
                phoneme = {}
                phoneme['phone'] = parts[0].split(': ')[1]
                phoneme['duration'] = float(parts[1].split(': ')[1])
                words[-1]['phones'].append(phoneme)

        self.result = words

    def get_final(self):
        return self.result

if __name__=='__main__':
    import numm3
    import sys

    infile = sys.argv[1]
    
    k = Kaldi()

    buf = numm3.sound2np(infile, nchannels=1, R=8000)
    logger.debug(f'loaded_buf {len(buf)}')
    
    idx=0
    while idx < len(buf):
        k.push_chunk(buf[idx:idx+160000].tostring())
        print(k.get_final())
        idx += 160000
