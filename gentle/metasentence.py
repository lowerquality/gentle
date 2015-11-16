import re

def load_vocabulary(words_file):
    return set([X.split(' ')[0] for X in open(words_file).read().split('\n')])

def kaldi_normalize(txt, vocab):
    # lowercase
    norm = txt.lower()
    # preserve in-vocab hyphenated phrases
    if norm in vocab:
        return [norm]
    # turn hyphens into spaces
    norm = norm.replace('-', ' ')
    # remove all punctuation
    norm = re.sub(r'[^a-z0-9\s\']', ' ', norm)
    seq = norm.split()
    # filter out empty words
    seq = [x.strip() for x in seq if len(x.strip())>0]
    # replace [oov] words
    seq = [x if x in vocab else '[oov]' for x in seq]

    return seq

class MetaSentence:
    """Maintain two parallel representations of a sentence: one for
    Kaldi's benefit, and the other in human-legible form.
    """

    def __init__(self, sentence, vocab):
        self.raw_sentence = sentence
        self.vocab = vocab

        self._gen_kaldi_seq(sentence)

    def _gen_kaldi_seq(self, sentence):
        self._seq = []
        parts = sentence.replace('\n', '\n ').split(' ')
        for part in parts:
            if len(part.strip()) == 0:
                continue
            self._seq.append({
                "display": part,
                "kaldi": kaldi_normalize(part, self.vocab)
            })

    def get_kaldi_sequence(self):
        return reduce(lambda acc,y: acc+y["kaldi"], self._seq, [])

    def get_matched_kaldi_sequence(self):
        return ['-'.join(X["kaldi"]) for X in self._seq]

    def get_display_sequence(self):
        return [X["display"] for X in self._seq]

    def align_from_kaldi(self, kaldi_alignment):
        """Return the display sentence, based on the alignment of the kaldi
        sentence
        """

        if len(self._seq) == 0:
            print 'no sequence?'
            return []
        
        display_timing = []
        cur_s_idx = 0
        cur_display_wd = {"word": self._seq[0]["display"]}
        
        started = False
        
        for wd in kaldi_alignment:
            s = self._seq[cur_s_idx]
            
            if len(s["kaldi"]) == 0:
                print 'k0', s
                cur_s_idx += 1
                if cur_s_idx == len(self._seq):
                    # Done!
                    cur_display_wd["word"] += "."
                    break
                cur_display_wd = {"word": self._seq[cur_s_idx]["display"]}
                s = self._seq[cur_s_idx]
                
            if s["kaldi"][0] == wd["word"]:
                # This is the first word in the chunk
                cur_display_wd["start"] = wd["start"]
                started = True
            if started and s["kaldi"][-1] == wd["word"]:
                # This is the last word in the chunk
                end = wd["start"] + wd["duration"]
                cur_display_wd["duration"] = end - cur_display_wd["start"]
                cur_s_idx += 1

                display_timing.append(cur_display_wd)
                started = False
                if cur_s_idx == len(self._seq):
                    # Done!
                    cur_display_wd["word"] += "."
                    break

                cur_display_wd = {"word": self._seq[cur_s_idx]["display"]}
            else:
                print 'what is this case?', 's', s, 'wd', wd, 'started', started

                #import pdb; pdb.set_trace()

        print 'AFK - DISPLAY TIMING', display_timing
        return display_timing
