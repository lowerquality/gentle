import subprocess
import os
import tempfile
from generate_wp import wordpair_from_word_sequence

WORDS_FILE = 'PROTO_LANGDIR/graphdir/words.txt' # XXX: path cannot have spaces
TXT_FST_SCRIPT = './kaldi/egs/rm/s5/local/make_rm_lm.pl'
ENV = os.environ
ENV["PATH"] += ":" + os.path.abspath("kaldi/src/fstbin/")
ENV["PATH"] += ":" + os.path.abspath("kaldi/src/bin/")
ENV["PATH"] += ":" + os.path.abspath("kaldi/tools/openfst/bin/")
MKGRAPH_WD = "kaldi/egs/wsj/s5/utils/"

PROTOTYPE_LANGUAGE_DIR = 'PROTO_LANGDIR/'

def getLanguageModel(kaldi_seq):
    """Generates a language model to fit the text

    `kaldi_seq` is a list of words within kaldi's vocabulary.
    """

    # Create a language model directory
    lang_model_dir = tempfile.mkdtemp()
    print 'saving language model to', lang_model_dir

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

    # Save the wordpair
    wordpair_file = os.path.join(lang_model_dir, 'wordpairs.txt')
    wordpair_from_word_sequence(kaldi_seq, wordpair_file)

    # Generate a textual FST
    txt_fst_file = os.path.join(lang_model_dir, 'G.txt')
    open(txt_fst_file, 'w').write(
        subprocess.check_output([TXT_FST_SCRIPT, wordpair_file]))
    

    # Generate a binary FST
    bin_fst_file = os.path.join(lang_model_dir, 'langdir', 'G.fst')
    open(bin_fst_file, 'w').write(subprocess.check_output([
        'fstcompile',
        '--isymbols=%s' % (WORDS_FILE),
        '--osymbols=%s' % (WORDS_FILE),
        '--keep_isymbols=false',
        '--keep_osymbols=false',
        txt_fst_file]))
              
    # Create the full HCLG.fst graph
    subprocess.call(['./mkgraph.sh',
                     os.path.join(lang_model_dir, 'langdir'),
                     os.path.join(lang_model_dir, 'modeldir'),
                     os.path.join(lang_model_dir, 'graphdir')],
                    env=ENV, cwd=MKGRAPH_WD)

    # Return the language model directory
    return lang_model_dir

if __name__=='__main__':
    import sys
    getLanguageModel(open(sys.argv[1]).read())
