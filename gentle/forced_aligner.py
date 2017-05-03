from gentle import diff_align
from gentle import kaldi_queue
from gentle import language_model
from gentle import metasentence
from gentle import multipass
from gentle.transcriber import MultiThreadedTranscriber
from gentle.transcription import Transcription

class ForcedAligner():

    def __init__(self, resources, transcript, nthreads=4, **kwargs):
        self.kwargs = kwargs
        self.nthreads = nthreads
        self.transcript = transcript
        self.resources = resources
        self.ms = metasentence.MetaSentence(transcript, resources.vocab)
        ks = self.ms.get_kaldi_sequence()
        gen_hclg_filename = language_model.make_bigram_language_model(ks, resources.proto_langdir, **kwargs)
        self.queue = kaldi_queue.build(resources, hclg_path=gen_hclg_filename, nthreads=nthreads)
        self.mtt = MultiThreadedTranscriber(self.queue, nthreads=nthreads)

    def transcribe(self, wavfile, progress_cb=None, logging=None):
        words, duration = self.mtt.transcribe(wavfile, progress_cb=progress_cb)

        # Clear queue (would this be gc'ed?)
        for i in range(self.nthreads):
            k = self.queue.get()
            k.stop()

        # Align words
        words = diff_align.align(words, self.ms, **self.kwargs)

        # Perform a second-pass with unaligned words
        if logging is not None:
            logging.info("%d unaligned words (of %d)" % (len([X for X in words if X.not_found_in_audio()]), len(words)))

        if progress_cb is not None:
            progress_cb({'status': 'ALIGNING'})

        words = multipass.realign(wavfile, words, self.ms, resources=self.resources, nthreads=self.nthreads, progress_cb=progress_cb)

        if logging is not None:
            logging.info("after 2nd pass: %d unaligned words (of %d)" % (len([X for X in words if X.not_found_in_audio()]), len(words)))

        words = AdjacencyOptimizer(words, duration).optimize()

        return Transcription(words=words, transcript=self.transcript)


class AdjacencyOptimizer():

    '''
    Sometimes there are ambiguous possible placements of not-found-in-audio
    words.  The word-based diff doesn't take into account intra-word timings
    when it does insertion, so can create strange results.  E.g. if the audio
    contains these words with timings like

        "She climbed on the bed and jumped on the mattress"
            0     1    2   3   4    5   6    7   8     9

    and suppose the speaker mumbled or there was noise obscuring the words
    "on the bed and jumped", so the hypothesis is just "She climbed on the mattress".

    The intended alignment would be to insert the missing out-of-audio words:

        "She climbed [on the bed and jumped] on the mattress"
            0     1                            7   8     9

    But the word-based diff might instead align "on the" with the first
    occurrence, and so insert out-of-audio words like this:

        "She climbed on the [bed and jumped on the] mattress"
            0     1    7   8                             9

    with a big gap in between "climbed" and "on" and no time available for
    "[bend and jumped on the]".

    Or imagine a case such as "I really really really really want to do
    this", where only one of the "really"s is in the hypothesis, so again
    the choice word-based choice of which to align it with is arbitrary.

    This method cleans those up, by checking each not-found-in-audio sequence
    of words to see if its neighbor(s) are candidates for moving inward and
    whether doing so would improve adjacent intra-word distances.
    '''

    def __init__(self, words, duration):
        self.words = words
        self.duration = duration

    def out_of_audio_sequence(self, i):
        j = i
        while 0 <= j < len(self.words) and self.words[j].not_found_in_audio():
            j += 1
        return None if j == i else j

    def tend(self, i):
        for word in reversed(self.words[:i]):
            if word.success():
                return word.end
        return 0

    def tstart(self, i):
        for word in self.words[i:]:
            if word.success():
                return word.start
        return self.duration

    def find_subseq(self, i, j, p, n):
        for k in range(i, j-n+1):
            for m in range(p, p+n):
                if self.words[k].word != self.words[m].word:
                    break
            else:
                return k
        return None

    def swap_adjacent_if_better(self, i, j, n, side):
        '''Given an out-of-audio sequence at [i,j), looks to see if the adjacent n words
        can be beneficially swapped with a subsequence.'''

        # construct adjacent candidate words and their gap relative to their
        # opposite neighbors
        if side == "left":
            p, q = (i-n, i)
            if p < 0: return False
            opp_gap = self.tstart(p) - self.tend(p)
        else:
            p, q = (j, j+n)
            if q > len(self.words): return False
            opp_gap = self.tstart(q) - self.tend(q)

        # is there a matching subsequence?
        k = self.find_subseq(i, j, p, n)
        if k is None: return False

        # if the opposite gap isn't bigger than the sequence gap, no benefit to
        # potential swap
        seq_gap = self.tstart(j) - self.tend(i)
        if opp_gap <= seq_gap: return False

        # swap subsequences at p and k
        for m in range(0, n):
            self.words[k+m].swap_alignment(self.words[p+m])

        return True

    def optimize_adjacent(self, i, j):
        '''Given an out-of-audio sequence at [i,j), looks for an opportunity to
        swap a sub-sequence with adjacent words at [p, i) or [j, p)'''

        for n in reversed(range(1, (j-i)+1)): # consider larger moves first
            if self.swap_adjacent_if_better(i, j, n, "left"): return True
            if self.swap_adjacent_if_better(i, j, n, "right"): return True

    def optimize(self):
        i = 0
        while i < len(self.words):
            j = self.out_of_audio_sequence(i)
            if j is None:
                i += 1

            elif self.optimize_adjacent(i, j):
                # back up to rescan in case we swapped left
                while i >= 0 and self.words[i].not_found_in_audio():
                    i -= 1

            else:
                i = j # skip past this sequence

        return self.words
