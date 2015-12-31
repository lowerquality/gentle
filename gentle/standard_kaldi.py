'''Glue code for communicating with standard_kaldi C++ process'''
import logging
import os
import subprocess
import wave
import tempfile

from gentle.paths import get_binary
from gentle import ffmpeg, prons

EXECUTABLE_PATH = get_binary("ext/standard_kaldi")

class Kaldi(object):
    '''Kaldi spawns a standard_kaldi subprocess and provides a
    Python wrapper for communicating with it.'''
    def __init__(
            self,
            nnet_dir='data/nnet_a_gpu_online',
            hclg_path='data/graph/HCLG.fst',
            proto_langdir='PROTO_LANGDIR'):
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

    def _write(self, data):
        """Send data to the subprocess, print stderr and raise if it crashes"""
        if self._stopped:
            # TODO(maxhawkins): I don't like how this API self-destructs after
            # use. The subprocess should stay open until the user specifically
            # deletes it.
            raise RuntimeError('wrote to stopped standard_kaldi process')
        try:
            self._subprocess.stdin.write(data)
        except IOError, _:
            raise IOError("Lost connection with standard_kaldi subprocess")

    def _cmd(self, name):
        """Begin a command"""
        self._write("%s\n" % (name))
        self._subprocess.stdin.flush()

    def push_chunk(self, buf):
        '''Push a chunk of audio. Returns true if it worked OK.'''
        # Wait until we're ready
        self._cmd("push-chunk")
        self._write("%d\n" % len(buf))
        self._write(buf)
        status = self._subprocess.stdout.readline().strip()
        return status == 'ok'

    def get_partial(self):
        '''Dump the provisional (non-word-aligned) transcript'''
        self._cmd("get-partial")
        words = []
        while True:
            line = self._subprocess.stdout.readline()
            logging.info("partial: %s", line)
            if line.startswith("ok"):
                break
            if parts[0].startswith('word'):
                word = parts[0].split(': ')[1]
                words.append(word)
        return words.join(" ")

    def get_final(self):
        '''Dump the final, phone-aligned transcript'''
        self._cmd("get-final")
        words = []
        while True:
            line = self._subprocess.stdout.readline()
            logging.info(line)
            if line.startswith("ok"):
                break
            parts = line.split(' / ')
            if parts[0].startswith('word'):
                word = {}
                word['word'] = parts[0].split(': ')[1]
                word['start'] = float(parts[1].split(': ')[1])
                word['duration'] = float(parts[2].split(': ')[1])
                word['phones'] = []
                words.append(word)
            elif parts[0].startswith('phone'):
                word = words[-1]
                phones = word['phones']
                phone = {}
                phone['phone'] = parts[0].split(': ')[1]
                phone['duration'] = float(parts[1].split(': ')[1])
                phones.append(phone)

        words = prons.tweak(words)
        return words

    def reset(self):
        '''Reset the decoder, delete the decoding state'''
        self._cmd("reset")

    def stop(self):
        '''Quit the program'''
        logging.info('stopping...')
        self._cmd("stop")
        self._subprocess.wait()
        logging.info('stopped\n')
        self._stopped = True

    def transcribe(self, infile):
        '''Read the given file as a wav and output a transcription'''
        words = []
        for words in self.transcribe_progress(infile):
            pass
        return words

    def transcribe_progress(self, infile, batch_size=10):
        '''Read the given file as a wav and output a transcription with progress.'''
        words = []

        yield {
            "words": words,
        }

        input_wav = read_wav(infile)

        def _add_words_arr(wds, arr, offset):
            '''Add the output from the decoder to our data structure, accounting
            for words that have been duplicated due to boundary conditions'''
            # There may be some overlap between the end of the last
            # transcription and the beginning of this one.
            #
            # First approach: remove the last item of `arr' and
            # start afterwards.
            lst = None
            if len(arr) > 0:
                lst = arr[-1]
                if lst["start"] > offset:
                    logging.info('trimming %s', lst)
                    arr.pop()

            for word in wds:
                word["start"] += offset
                if lst is not None and (word["start"] - lst["start"]) < -0.05:
                    logging.info('skipping %s %f\n', word, (word["start"] - lst["start"]))
                    continue
                arr.append(word)

        def _add_words(wds, offset):
            '''Add the output from the decoder to our data structure and
            optionally send the partial results to a status callback'''
            _add_words_arr(wds, words, offset)

        idx = 0
        seg_offset = 0
        while True:
            chunk_size = 16000 # frames (2sec)
            chunk = input_wav.readframes(chunk_size)

            self.push_chunk(chunk)

            if idx > 0 and idx % batch_size == 0:
                logging.info('endpoint!\n')
                ret = self.get_final()
                _add_words(ret, seg_offset*2)
                yield {
                    "words": words,
                }

                self.reset()
                seg_offset = idx

                # Push same chunk again
                self.push_chunk(chunk)

            # if idx > 0 and idx % 5 == 0:
            #     # ...just to show some progress
            #     logging.info('%s\n' % k.get_partial())
            #     # XXX: expose in a callback?

            if len(chunk) != (chunk_size * input_wav.getsampwidth()):
                break

            idx += 1

        logging.info('done with audio!')
        ret = self.get_final()
        self.reset()
        _add_words(ret, seg_offset*2)
        yield {
            "words": words,
        }

    def __del__(self):
        if not self._stopped:
            self.stop()

def read_wav(infile):
    '''
    Create a stdlib wave object from the given input file.

    If the file isn't a wav or has the wrong sample format,
    try to convert it using ffmpeg.
    '''
    try:
        input_wav = wave.open(infile, 'r')
    except wave.Error, _:
        input_wav = wave.open(ffmpeg.to_wav(infile), 'r')

    if input_wav.getnchannels() != 1:
        raise ValueError("input wav must be mono")
    if input_wav.getframerate() != 8000:
        raise ValueError("input wav must have 8kHZ sample rate")
    if input_wav.getsampwidth() != 2:
        raise ValueError("input wav must have 16 bit depth")

    return input_wav

def main():
    '''Transcribe the given input file using a standard_kaldi C++ subprocess.'''
    import sys
    import json

    infile = sys.argv[1]
    outfile = sys.argv[2]

    if len(sys.argv) > 5:
        nnet_dir = sys.argv[3]
        graph_dir = sys.argv[4]
        proto_langdir = sys.argv[5]
        k = Kaldi(nnet_dir, graph_dir, proto_langdir)
    else:
        k = Kaldi()

    words = None
    for words in k.transcribe_progress(infile, batch_size=1):
        sys.stderr.write(".")
    sys.stderr.write("\n")
    with open(outfile, 'w') as out:
        json.dump(words, out, indent=2)

if __name__ == '__main__':
    main()
