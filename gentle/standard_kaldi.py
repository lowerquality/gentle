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

        cmd = [EXECUTABLE_PATH]

        if nnet_dir is not None:
            cmd.append(nnet_dir)
            cmd.append(hclg_path)

        if not os.path.exists(hclg_path):
            logger.error('hclg_path does not exist: %s', hclg_path)
        
        logger.debug(f"{self.k3_id} Opening pipe with cmd {cmd}")

        self._p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL if suppress_stderr else sys.stderr, 
            bufsize=0
        )

    def _cmd(self, c):
        self._write(f"{c}\n")
        self._p.stdin.flush()

    def _write(self, data, encoded=False):
        binary = data if encoded else data.encode()

        if encoded:
            logger.debug(f"{self.k3_id} Writing bytes to k3 {len(data)}")
        else:
            logger.debug(f"{self.k3_id} Writing cmd to k3 {data.strip()}")
        
        self._p.stdin.write(binary)

    def _read(self):
        output = self._p.stdout.readline().strip().decode()
        logger.debug(f"{self.k3_id} Reading from k3 {output}")
        return output

    def push_chunk(self, buf):
        # Wait until we're ready
        self._cmd("push-chunk")
        
        cnt = int(len(buf)/2)
        self._cmd(str(cnt))
        self._write(buf, encoded=True) #arr.tostring())
        status = self._read()
        return status == 'ok'

    def get_final(self):
        self._cmd("get-final")
        words = []
        while True:
            line = self._read()
            if line.startswith("done"):
                break
            parts = line.split(' / ')
            if line.startswith('word'):
                wd = {}
                wd['word'] = parts[0].split(': ')[1]
                wd['start'] = float(parts[1].split(': ')[1])
                wd['duration'] = float(parts[2].split(': ')[1])
                wd['phones'] = []
                words.append(wd)
            elif line.startswith('phone'):
                ph = {}
                ph['phone'] = parts[0].split(': ')[1]
                ph['duration'] = float(parts[1].split(': ')[1])
                words[-1]['phones'].append(ph)

        self._reset()
        return words

    def _reset(self):
        self._cmd("reset")

    def stop(self):
        if not self.finished:
            self.finished = True
            self._cmd("stop")
            self._p.stdin.close()
            self._p.stdout.close()
            self._p.wait()

    def __del__(self):
        self.stop()

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
