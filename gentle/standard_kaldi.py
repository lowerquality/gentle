'''Glue code for communicating with standard_kaldi C++ process'''
import logging
import os
import re
import subprocess
import wave

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

    def get_words(self):
        '''Memoized version of _get_words'''
        if self._words is None: # memoize
            self._words = self._get_words()
        return self._words

    def _get_words(self):
        '''Load vocabulary words from an OpenFST SymbolTable formatted text file'''
        path = os.path.join(self.proto_langdir, "graphdir/words.txt")

        # Load from disk (could load from kaldi)
        words = {}
        with open(path) as wordfile:
            for idx, line in enumerate(wordfile):
                words[idx] = line.split(' ')[0]
        return words

    def push_chunk(self, buf):
        '''Push a chunk of audio. Returns true if it worked OK.'''
        # Wait until we're ready
        self._cmd("push-chunk")
        self._write("%d\n" % len(buf))
        self._write(buf)
        status = self._subprocess.stdout.readline().strip()
        return status == 'ok'

    def get_transitions(self):
        '''Memoized version of _get_transitions'''
        if self._transitions is None:
            self._transitions = self._get_transitions()
        return self._transitions

    def _get_transitions(self):
        '''Dump transition information (for phoneme introspection)'''
        self._cmd("get-transitions")

        transitions = {}

        cur_trans_state = None
        while True:
            line = self._subprocess.stdout.readline().strip()
            if line.startswith("done"):
                break

            if line.startswith("Transition-state"):
                pattern = r'Transition-state (\d+): phone = ([^ ]*) hmm-state = (\d) pdf = (\d+)'
                match = re.match(pattern, line)
                if not match:
                    logging.error('err %s', line)
                    continue
                cur_trans_state = {"phone": match.group(2),
                                   "hmm-state": int(match.group(3)),
                                   "pdf": int(match.group(4))}
            else:
                pattern = r'Transition-id = (\d+) p = (\d\.\d+) \[([^\]]+)\]'
                match = re.match(pattern, line)
                if not match:
                    logging.error('err %s', line)
                    continue

                transitions[int(match.group(1))] = {
                    "state": cur_trans_state,
                    "p": float(match.group(2)),
                    "transition": match.group(3)
                }

        return transitions

    def _get_lattice(self):
        '''Read the subprocess output and parse it into a lattice data structure.'''
        lines = []
        while True:
            line = self._subprocess.stdout.readline().strip()

            # For example:
            # 17   18   112030   5.58026,-10.5059,30270_30269_30269_30422_30421_30421_30421_\
            # 30620_30619_43462_43461_43461_43461_43461_43461_43588_43716_2_1_1_1_1_1_1_8_5_\
            # 5_5_5_5_5_5_5_5_5_5_5_5_5_5_5_5_5_5_5_18_17_17_2136_2135_2135_2135_2135_2522_2\
            # 521_3112_36394_36393_36688_36687_36696_11238_11420_11656_13070_13262_13352_133\
            # 51_1598_1597_1597_1718_1717_1806_46352_46351_46528_46790_43422
            #
            # compact lattice
            # acceptors
            # weights: a pair of floats, and a sequence of integers
            #
            # input symbol and output symbol are identical -- represent words
            # This seems to be the third integer
            #
            # I'd guess that the first two are "from_state" and "to_state"
            #
            # in a normal (non-compact) lattice, the input symbol is a transition_id,
            # and the output symbol is a word
            #
            # the ints are a "sequence of transition_ids"
            # the transition_ids resolve to (phone, hmm-state, pdf)
            #
            # (is that true? or are those transition-states? how do we get
            # tuple/phoneme/whatever from id?)
            #
            # pdf is a "probability distribution function"
            # hmm-state is { 0, 1, 2 } and refers to the "pdf class"
            # state `1' is "central" (duh? what does that mean?)
            #
            # pdf's *sort-of* map to phonemes, but it's a blurry 1-1 (?)
            #
            # the floats are: graph cost, acoustic cost (respectively)
            # we'll call those (a,b)
            #
            # for openfst "semiring" would be something like (a+b, a-b)
            # the acoustic costs are scaled, so they may need to be unscaled for some
            # purposes (why?) - "The acoustic scale is the scale applied to the acoustics
            # (i.e. to the log-likelihood of a frame given an acoustic state)"

            if line.startswith('done'):
                break

            if len(line) > 0:
                arc = {}

                tabs = line.split('\t')
                arc["from_state"] = int(tabs[0])
                if len(tabs) > 1:
                    if len(tabs) > 2:
                        arc["to_state"] = int(tabs[1])
                        arc["word"] = int(tabs[2])

                    weights = tabs[-1].split(",")
                    arc["graph_cost"] = float(weights[0])
                    arc["acoustic_cost"] = float(weights[1])
                    if len(weights[2]) > 0:
                        arc["transition_ids"] = [int(X) for X in weights[2].split("_")]
                lines.append(arc)

        return lines

    def get_lattice(self):
        '''Dump the provisional (non-word-aligned) lattice.'''
        self._cmd("get-lattice")
        return self._get_lattice()

    def get_final_lattice(self):
        '''Dump the final word-aligned lattice.'''
        self._cmd("get-final-lattice")
        return self._get_lattice()

    def clean_lattice(self, ret):
        '''
        Do some clean-up on the lattices returned by standard_kaldi:
          * map word-ids to actual words from the vocabulary
          * remove duplicate phone transitions
        '''
        # construct lattice independencty
        output = {}

        # Swap in useful things in place of IDs
        for arc in ret:
            if arc.get("word"):
                arc["word"] = self.get_words().get(arc["word"])
            if arc.get("transition_ids"):
                # Dedupe transitions
                trans = []
                for trans_id in arc["transition_ids"]:
                    t_obj = self.get_transitions()[trans_id]
                    if len(trans) == 0 or trans[-1]["phone"] != t_obj["state"]["phone"]:
                        phone = {"phone": t_obj["state"]["phone"], "length": 1}
                        trans.append(phone)
                    else:
                        trans[-1]["length"] += 1

                arc["transitions"] = trans
                del arc["transition_ids"]

            output.setdefault(arc["from_state"], []).append(arc)

        return output

    def get_partial(self):
        '''Dump the provisional (non-word-aligned) transcript'''
        self._cmd("get-partial")
        return self._subprocess.stdout.readline()

    def get_final(self):
        '''Dump the final, word-aligned transcript'''
        self._cmd("get-final")
        words = []
        while True:
            line = self._subprocess.stdout.readline()
            if line.startswith("done"):
                break
            parts = line.split(' / ')
            word = {}
            word['word'] = parts[0].split(': ')[1]
            word['start'] = float(parts[1].split(': ')[1])
            word['duration'] = float(parts[2].split(': ')[1])
            words.append(word)
        return words

    def get_prons(self):
        '''Dump the final, phone-aligned transcript'''
        self._cmd("get-prons")
        words = []
        while True:
            line = self._subprocess.stdout.readline()
            if line.startswith("done"):
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

    def peek_final(self):
        ''''Dump the final, word-aligned transcript, but don't finalize decoding.'''
        self._cmd("peek-final")
        words = []
        while True:
            line = self._subprocess.stdout.readline()
            if line.startswith("done"):
                break
            parts = line.split(' / ')
            word = {}
            word['word'] = parts[0].split(': ')[1]
            word['start'] = float(parts[1].split(': ')[1])
            word['duration'] = float(parts[2].split(': ')[1])
            words.append(word)
        return words

    def reset(self):
        '''Reset the decoder, delete the decoding state'''
        self._cmd("reset")

    def continue_(self):
        '''Update iVectors and continue with current speaker'''
        self._cmd("continue")

    def stop(self):
        '''Quit the program'''
        logging.info('stopping...')
        self._cmd("stop")
        self._subprocess.wait()
        logging.info('stopped\n')
        self._stopped = True

    def __del__(self):
        if not self._stopped:
            self.stop()

def lattice(k, infile):
    '''Read the given file as a wav and output a computed lattice data structure'''
    # TODO: Merge into a single ID -> Arc dictionary
    lat = []

    input_wav = read_wav(infile)

    def _add_lattice(ret, offset):
        '''Clean the lattice and put it in the data structure'''
        # First, construct lattice independenctly
        cleaned_lat = k.clean_lattice(ret)
        lat.append({
            "start": offset,
            "lattice": cleaned_lat
        })

    idx = 0
    seg_offset = 0
    while True:
        chunk_size = 16000 # frames (2sec)
        chunk = input_wav.readframes(chunk_size)

        logging.info('%d %d', idx, len(chunk))

        k.push_chunk(chunk)

        if idx > 0 and idx % 15 == 0:
            logging.info('endpoint!\n')
            ret = k.get_final()
            _add_lattice(ret, seg_offset*2)

            k.reset()
            seg_offset = idx

            # Push same chunk again
            k.push_chunk(chunk)

        if len(chunk) != (chunk_size * input_wav.getsampwidth()):
            break

        idx += 1

    logging.info('done with audio!')
    ret = k.get_final()
    _add_lattice(ret, seg_offset*2)
    k.stop()
    return lat

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


def transcribe(k, infile, batch_size=10,
               partial_results_cb=None, partial_results_kwargs=None):
    '''Read the given file as a wav and output a transcription'''
    words = []

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
        if partial_results_cb is not None:
            partial_results_cb(wds, **partial_results_kwargs)

    idx = 0
    seg_offset = 0
    while True:
        chunk_size = 16000 # frames (2sec)
        chunk = input_wav.readframes(chunk_size)

        k.push_chunk(chunk)

        if idx > 0 and idx % batch_size == 0:
            logging.info('endpoint!\n')
            ret = k.get_prons()
            _add_words(ret, seg_offset*2)

            k.reset()
            seg_offset = idx

            # Push same chunk again
            k.push_chunk(chunk)

        # if idx > 0 and idx % 5 == 0:
        #     # ...just to show some progress
        #     logging.info('%s\n' % k.get_partial())
        #     # XXX: expose in a callback?

        if len(chunk) != (chunk_size * input_wav.getsampwidth()):
            break

        idx += 1

    logging.info('done with audio!')
    ret = k.get_prons()
    _add_words(ret, seg_offset*2)
    k.stop()
    return {"words": words}

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

    words = transcribe(k, infile)
    with open(outfile, 'w') as out:
        json.dump(words, out, indent=2)

if __name__ == '__main__':
    main()
