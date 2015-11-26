import logging
import math
import os
import subprocess
import sys
import tempfile

from paths import get_binary
from metasentence import MetaSentence

MKGRAPH_PATH = get_binary("mkgraph")

def make_bigram_lm_fst(word_sequence):
    '''
    Use the given token sequence to make a bigram language model
    in OpenFST plain text format.
    '''
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

def get_language_model(kaldi_seq, proto_langdir='PROTO_LANGDIR'):
    """Generates a language model to fit the text

    `proto_langdir` is a path to a directory containing prototype model data
    `kaldi_seq` is a list of words within kaldi's vocabulary.
    """

    # Create a language model directory
    lang_model_dir = tempfile.mkdtemp()
    logging.info('saving language model to %s', lang_model_dir)

    # Symlink in necessary files from the prototype directory
    for dirpath, dirnames, filenames in os.walk(proto_langdir, followlinks=True):
        for dirname in dirnames:
            relpath = os.path.relpath(os.path.join(dirpath, dirname), proto_langdir)
            os.makedirs(os.path.join(lang_model_dir, relpath))
        for filename in filenames:
            abspath = os.path.abspath(os.path.join(dirpath, filename))
            relpath = os.path.relpath(os.path.join(dirpath, filename), proto_langdir)
            dstpath = os.path.join(lang_model_dir, relpath)
            os.symlink(abspath, dstpath)

    # Generate a textual FST
    txt_fst = make_bigram_lm_fst(kaldi_seq)
    txt_fst_file = os.path.join(lang_model_dir, 'G.txt')
    open(txt_fst_file, 'w').write(txt_fst)
    
    words_file = os.path.join(proto_langdir, "graphdir/words.txt")
    subprocess.check_output([MKGRAPH_PATH,
                     os.path.join(lang_model_dir, 'langdir'),
                     os.path.join(lang_model_dir, 'modeldir'),
                     txt_fst_file,
                     words_file,
                     os.path.join(lang_model_dir, 'graphdir', 'HCLG.fst')])

    # Return the language model directory
    return lang_model_dir

if __name__=='__main__':
    import sys
    get_language_model(open(sys.argv[1]).read())
