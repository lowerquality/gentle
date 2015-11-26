# Take a transcript, and generate a textual FST containing a bigram language model

import sys
import re
import math

from metasentence import MetaSentence

def language_model_from_word_sequence(word_sequence):
    word_sequence = ['[oov]', '[oov]'] + word_sequence + ['[oov]']

    bigrams = {}
    prev_word = word_sequence[0]
    for word in word_sequence[1:]:
        bigrams.setdefault(prev_word, set()).add(word)
        prev_word = word

    node_ids = {}
    def get_node_id(word):
        node_id = node_ids.get(word, len(node_ids) + 1)
        node_ids[word] = node_id
        return node_id

    output = ""
    for from_word in sorted(bigrams.keys()):
        from_id = get_node_id(from_word)

        successors = bigrams[from_word]
        if len(successors) > 0:
            weight = -math.log(1.0 / len(successors))
        else:
            weight = 0

        for to_word in sorted(successors):
            to_id = get_node_id(to_word)
            output += '%d    %d    %s    %s    %f' % (from_id, to_id, to_word, to_word, weight)
            output += "\n"

    output += "%d    0\n" % (len(node_ids))

    return output


if __name__=='__main__':
    USAGE = "python generate_wp.py WORDS.TXT TRANSCRIPT OUTPUT_FILE"
    if len(sys.argv) != 4:
        print USAGE
        sys.exit(1)

    WORDS_FILE = sys.argv[1]
    TRANSCRIPT_FILE = sys.argv[2]
    OUTPUT_FILE = sys.argv[3]

    vocabulary = set([X.split(' ')[0] for X in open(WORDS_FILE).read().split('\n')])
    transcript = open(TRANSCRIPT_FILE).read()

    ms = MetaSentence(transcript, vocabulary)
    word_sequence = ms.get_kaldi_sequence()
    lm = language_model_from_word_sequence(word_sequence)
    open(OUTPUT_FILE, 'w').write(lm)
