# coding=utf-8
import re

def load_vocabulary(words_file):
    return set([X.split(' ')[0] for X in open(words_file).read().split('\n')])

def kaldi_normalize(word, vocab):
    """
    Take a token extracted from a transcript by MetaSentence and
    transform it to use the same format as Kaldi's vocabulary files.
    Removes fancy punctuation and strips out-of-vocabulary words.
    """
    # lowercase
    norm = word.lower()
    # Turn fancy apostrophes into simpler apostrophes
    norm = norm.replace("’", "'")
    if len(norm) > 0 and not norm in vocab:
        norm = '[oov]'
    return norm

class MetaSentence:
    """Maintain two parallel representations of a sentence: one for
    Kaldi's benefit, and the other in human-legible form.
    """

    def __init__(self, sentence, vocab):
        self.raw_sentence = sentence
        self.vocab = vocab

        self._tokenize(sentence)

    def _tokenize(self, sentence):
        self._seq = []
        for m in re.finditer(r'(\w|\’\w|\'\w)+', sentence):
            start, end = m.span()
            word = m.group()
            if len(word.strip()) == 0:
                continue
            token = kaldi_normalize(word, self.vocab)
            self._seq.append({
                "start": start,
                "end": end,
                "token": token,
            })

    def get_kaldi_sequence(self):
        return [x["token"] for x in self._seq]

    def get_display_sequence(self):
        display_sequence = []
        for x in self._seq:
            start, end = x["start"], x["end"]
            word = self.raw_sentence[start:end]
            display_sequence.append(word)
        return display_sequence

    def get_text_offsets(self):
        return [(x["start"], x["end"]) for x in self._seq]
