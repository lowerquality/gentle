import os
import re
import subprocess
import numpy as np

EXECUTABLE_PATH = "./standard_kaldi"

class Kaldi:
    def __init__(self, language_model='data/graph/HCLG.fst'):

        # make sure we're using the right language model
        # H_PATH = 'HCLG.fst'
        # if os.path.exists(H_PATH):
        #     os.unlink(H_PATH)
        # os.symlink(language_model, H_PATH)
        
        self._p = subprocess.Popen([EXECUTABLE_PATH, language_model],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        self._transitions = None
        self._words = None
        

    def _cmd(self, c):
        self._p.stdin.write("%s\n" % (c))
        self._p.stdin.flush()

    def get_words(self):
        # memoize
        if self._words is None:
            self._words = self._get_words()
        return self._words
    
    def _get_words(self, path="PROTO_LANGDIR/graphdir/words.txt"):
        # Load from disk (could load from kaldi)
        words = {}
        for idx,line in enumerate(open(path)):
            words[idx] = line.split(' ')[0]
        return words

    def push_chunk(self, arr):
        # Wait until we're ready
        self._cmd("push-chunk")
        self._p.stdin.write(arr.tostring())
        status = self._p.stdout.readline().strip()
        return status == 'ok'

    def get_transitions(self):
        # memoize
        if self._transitions is None:
            self._transitions = self._get_transitions()
        return self._transitions

    def _get_transitions(self):
        self._cmd("get-transitions")

        transitions = {}

        cur_trans_state = None
        while True:
            line = self._p.stdout.readline().strip()
            if line.startswith("done"):
                break

            if line.startswith("Transition-state"):
                m = re.match(r'Transition-state (\d+): phone = ([^ ]*) hmm-state = (\d) pdf = (\d+)', line)
                if not m:
                    print 'err', line
                    continue
                cur_trans_state = {"phone": m.group(2),
                                   "hmm-state": int(m.group(3)),
                                   "pdf": int(m.group(4))}
            else:
                m = re.match(r'Transition-id = (\d+) p = (\d\.\d+) \[([^\]]+)\]', line)
                if not m:
                    print 'err', line
                    continue

                transitions[int(m.group(1))] = {"state": cur_trans_state,
                                                "p": float(m.group(2)),
                                                "transition": m.group(3)}

        return transitions

    def _get_lattice(self):
        lines = []
        while True:
            line = self._p.stdout.readline().strip()

            # For example:
            #17   18   112030   5.58026,-10.5059,30270_30269_30269_30422_30421_30421_30421_30620_30619_43462_43461_43461_43461_43461_43461_43588_43716_2_1_1_1_1_1_1_8_5_5_5_5_5_5_5_5_5_5_5_5_5_5_5_5_5_5_5_5_18_17_17_2136_2135_2135_2135_2135_2522_2521_3112_36394_36393_36688_36687_36696_11238_11420_11656_13070_13262_13352_13351_1598_1597_1597_1718_1717_1806_46352_46351_46528_46790_43422
            
            # compact lattice
            # acceptors
            # weights: a pair of floats, and a sequence of integers

            # input symbol and output symbol are identical -- represent words
            # This seems to be the third integer

            # I'd guess that the first two are "from_state" and "to_state"

            # in a normal (non-compact) lattice, the input symbol is a transition_id, and the output symbol is a word

            # the ints are a "sequence of transition_ids"
            # the transition_ids resolve to (phone, hmm-state, pdf)
            #
            # (is that true? or are those transition-states? how do we get tuple/phoneme/whatever from id?)
            
            # pdf is a "probability distribution function"
            # hmm-state is { 0, 1, 2 } and refers to the "pdf class"
            # state `1' is "central" (duh? what does that mean?)

            # pdf's *sort-of* map to phonemes, but it's a blurry 1-1 (?)
            
            # the floats are: graph cost, acoustic cost (respectively)
            # we'll call those (a,b)

            # for openfst "semiring" would be something like (a+b, a-b)
            # the acoustic costs are scaled, so they may need to be unscaled for some purposes (why?)
            #  - "The acoustic scale is the scale applied to the acoustics (i.e. to the log-likelihood of a frame given an acoustic state)"
            
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
        self._cmd("get-lattice")
        return self._get_lattice()
    def get_final_lattice(self):
        self._cmd("get-final-lattice")
        return self._get_lattice()

    def clean_lattice(self, ret):
        # construct lattice independenctly
        mLat = {}
        
        # Swap in useful things in place of IDs
        for arc in ret:
            if arc.get("word"):
                arc["word"] = self.get_words().get(arc["word"])
            if arc.get("transition_ids"):
                # Dedupe transitions
                trans = []
                for t in arc["transition_ids"]:
                    t_obj = self.get_transitions()[t]
                    if len(trans) == 0 or trans[-1]["phone"] != t_obj["state"]["phone"]:
                        ph = {"phone": t_obj["state"]["phone"], "length": 1}
                        trans.append(ph)
                    else:
                        trans[-1]["length"] += 1

                arc["transitions"] = trans
                del arc["transition_ids"]

            mLat.setdefault(arc["from_state"], []).append(arc)

        return mLat
    

    def get_partial(self):
        self._cmd("get-partial")
        return self._p.stdout.readline()

    def get_final(self):
        self._cmd("get-final")
        words = []
        while True:
            line = self._p.stdout.readline()
            if line.startswith("done"):
                break
            parts = line.split(' / ')
            wd = {}
            wd['word'] = parts[0].split(': ')[1]
            wd['start'] = float(parts[1].split(': ')[1])
            wd['duration'] = float(parts[2].split(': ')[1])
            words.append(wd)
        return words


    def peek_final(self):
        self._cmd("peek-final")
        words = []
        while True:
            line = self._p.stdout.readline()
            if line.startswith("done"):
                break
            parts = line.split(' / ')
            wd = {}
            wd['word'] = parts[0].split(': ')[1]
            wd['start'] = float(parts[1].split(': ')[1])
            wd['duration'] = float(parts[2].split(': ')[1])
            words.append(wd)
        return words
    
    def reset(self):
        self._cmd("reset");

    def continue_(self):
        self._cmd("continue");

    def stop(self):
        print 'stopping...'
        self._cmd("stop")
        self._p.wait()
        print 'stopped'

    def __del__(self):
        self.stop()

def lattice(k, infile):
    import numm3
    # TODO: Merge into a single ID -> Arc dictionary
    lat = []

    def _add_lattice(ret, offset):
        # First, construct lattice independenctly
        mLat = k.clean_lattice(ret)
        lat.append({"start": offset, "lattice": mLat})

    start_idx = 0
    for idx,buf in enumerate(numm3.sound_chunks(infile, R=8000, chunksize=16000, nchannels=1)):
        buf = buf.reshape((-1))
        print idx, len(buf)
        
        if buf.shape[0] < 16000:
            print 'done with audio!'
            ret = k.get_final_lattice()
            _add_lattice(ret, start_idx*2)
            k.stop()
            return lat
        #elif not (k.push_chunk(buf) or idx == start_idx):
        k.push_chunk(buf)
        if idx > 0 and idx % 15 == 0:
            print 'endpoint!', idx*2
            ret = k.get_final_lattice()
            _add_lattice(ret, start_idx*2)
            k.reset()
            start_idx = idx
            # Push same chunk again
            k.push_chunk(buf)

def transcribe(k, infile):
    import numm3
    #phones = []
    words = []

    def _add_words_arr(wds, arr, offset):
        # There may be some overlap between the end of the last
        # transcription and the beginning of this one.
        #
        # First approach: remove the last item of `arr' and
        # start afterwards.
        lst = None
        if len(arr) > 0:
            lst = arr[-1]
            if lst["start"] > offset:
                print 'trimming', lst
                arr.pop()

        for w in wds:
            w["start"] += offset
            if lst is not None and (w["start"] - lst["start"]) < -0.05:
                print 'skipping', w, (w["start"] - lst["start"])
            elif lst is not None:
                print 'adding', w, (w["start"] - lst["start"])
            arr.append(w)

    def _add_words(wds, offset):
        _add_words_arr(wds, words, offset)

    start_idx = 0
    for idx,buf in enumerate(numm3.sound_chunks(infile, R=8000, chunksize=16000, nchannels=1)):
        buf = buf.reshape((-1))

        if buf.shape[0] < 16000:
            print 'done with audio!'
            ret = k.get_final()
            _add_words(ret, start_idx*2)
            k.stop()
            return {"words": words}
        k.push_chunk(buf)        
        if idx > 0 and idx % 15 == 0:
            print 'endpoint!'
            ret = k.get_final()
            _add_words(ret, start_idx*2)
            
            k.reset()
            start_idx = idx
            
            # Push same chunk again
            k.push_chunk(buf)

        if idx > 0 and idx % 5 == 0:
            # ...just to show some progress
            print k.get_partial()

if __name__=='__main__':
    import numm3
    import sys

    import json
    INFILE = sys.argv[1]
    OUTFILE= sys.argv[2]

    if len(sys.argv) > 3:
        k = Kaldi(sys.argv[3])
    else:
        k = Kaldi()

    words = transcribe(k, INFILE)
    json.dump(words, open(OUTFILE, 'w'), indent=2)
    #lat = lattice(k, INFILE)
    #json.dump(lat, open(OUTFILE, 'w'), indent=2)
