import re

def load_vocabulary(words_file):
    return set([X.split(' ')[0] for X in open(words_file).read().split('\n')])

class MetaSentence:
    """Maintain two parallel representations of a sentence: one for
    Kaldi's benefit, and the other in human-legible form.
    """

    def __init__(self, sentence, vocab):
        self.raw_sentence = sentence
        self.vocab = vocab

        self._seq = [{"display": X} for X in sentence.replace('\n', '\n ').split(' ') if len(X.strip()) > 0]
        self._gen_kaldi_seq()

    def _gen_kaldi_seq(self):
        for s in self._seq:
            # lowercase
            k = s["display"].lower()
            # turn hyphens into spaces
            k = k.replace('-', ' ')
            # remove all punctuation
            k = re.sub(r'[^a-z0-9\s\']', '', k)
            kseq = k.split()
            # filter out empty words
            kseq = [x.strip() for x in kseq if len(x.strip())>0]
            # replace [oov] words
            kseq = [x if x in self.vocab else '[oov]' for x in kseq]
            s["kaldi"] = kseq

    def get_kaldi_sequence(self):
        return reduce(lambda acc,y: acc+y["kaldi"], self._seq, [])

    def get_matched_kaldi_sequence(self):
        return ['-'.join(X["kaldi"]) for X in self._seq]

    def get_display_sequence(self):
        return [X["display"] for X in self._seq]

    def is_kaldi_done_naive(self, kaldi_partial_results):
        k_str = ' '.join(self.get_kaldi_sequence())
        return k_str in kaldi_partial_results

    def is_kaldi_done(self, kaldi_partial_results):
        # Check for length and last word and at least half of the desired words
        kseq = self.get_kaldi_sequence()
        pseq = kaldi_partial_results.split()

        hits = 0
        for k in kseq:
            if k in kaldi_partial_results:
                hits += 1

        ret = len(kseq) == 0 or len(pseq) >= len(kseq) and kseq[-1] in kaldi_partial_results and hits >= len(kseq)/2

        if ret:
            print 'Good enough.'
            print 'KPS', kaldi_partial_results
            print 'RS', self.raw_sentence

        return ret

    def is_kaldi_done_forgiving(self, kaldi_partial_results):
        # Check for length and last word
        kseq = self.get_kaldi_sequence()
        pseq = kaldi_partial_results.split()


        # XXX: Is it useful to make this non-binary?
        
        # We have two error cases:

        # Either we missed the sentence that we're looking for already
        # (and we'd be better off trying the next sentence)

        # Or the sentence is very far in the future, after a lot of
        # [oov]'s. Paradoxically, this latter case is likely to happen
        # if we prepare for the former.

        # If we have more than half [oov]'s by the 

        ret = len(pseq) >= len(kseq) and kseq[-1] in kaldi_partial_results

        if ret:
            print 'IKD!!'
            print kaldi_partial_results
            print self.raw_sentence

        return ret

    def _multi_align_from_kaldi(self, kaldi_alignment):
        # Try all of the possible starting locations
        start_indices = [(idx,X) for (idx,X) in enumerate(kaldi_alignment) if X["word"] == self._seq[0]["kaldi"][0]]
        print 'try starting from:', start_indices
        alignments = [self._align_from_kaldi(kaldi_alignment[idx:]) for idx,wd in start_indices]
        print 'There are %d possible alignments' % (len(alignments))
        # TODO: return the alignment with the largest number of aligned words
        return alignments[-1]

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
