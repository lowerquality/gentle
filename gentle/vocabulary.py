# coding=utf-8

def load_word_file(word_file):
    '''Load vocabulary words from an OpenFST SymbolTable formatted text file'''
    return set(line.split(' ')[0] for line in word_file if line != '')

class Vocabulary(object):
    def __init__(self, words):
        self.words = words

    @staticmethod
    def from_file(word_filename):
        with open(word_filename, 'r') as f:
            words = load_word_file(f)
        return Vocabulary(words)

    def normalize(self, word):
        """
        Take a text extracted from a transcript and transform it to
        use the same format as Kaldi's vocabulary files. Removes fancy
        punctuation and strips out-of-vocabulary words.
        """
        # lowercase
        norm = word.lower()
        # Turn fancy apostrophes into simpler apostrophes
        norm = norm.replace("’", "'")
        if len(norm) > 0 and not norm in self.words:
            norm = '[oov]'
        return norm
