from generate_wp import language_model_from_word_sequence
import os
import subprocess
import sys
import tempfile

KALDI_ROOT = "kaldi"
FST_BIN = KALDI_ROOT + "/tools/openfst/bin"

ENV = os.environ
ENV["PATH"] += ":" + os.path.abspath(KALDI_ROOT + "/src/fstbin/")
ENV["PATH"] += ":" + os.path.abspath(KALDI_ROOT + "/src/bin/")
ENV["PATH"] += ":" + os.path.abspath(FST_BIN)
MKGRAPH_WD = KALDI_ROOT + "/egs/wsj/s5/utils/"

def getLanguageModel(kaldi_seq, proto_langdir='PROTO_LANGDIR'):
    """Generates a language model to fit the text

    `proto_langdir` is a path to a directory containing prototype model data
    `kaldi_seq` is a list of words within kaldi's vocabulary.
    """

    # Create a language model directory
    lang_model_dir = tempfile.mkdtemp()
    sys.stderr.write('saving language model to %s\n' % lang_model_dir)

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
    txt_fst = language_model_from_word_sequence(kaldi_seq)
    txt_fst_file = os.path.join(lang_model_dir, 'G.txt')
    open(txt_fst_file, 'w').write(txt_fst)
    
    # TODO(maxhawkins): can this path have spaces?
    words_file = os.path.join(proto_langdir, "graphdir/words.txt")

    # Generate a binary FST
    bin_fst_file = os.path.join(lang_model_dir, 'langdir', 'G.fst')
    open(bin_fst_file, 'w').write(subprocess.check_output([
        'fstcompile',
        '--isymbols=%s' % (words_file),
        '--osymbols=%s' % (words_file),
        '--keep_isymbols=false',
        '--keep_osymbols=false',
        txt_fst_file]))
              
    # Create the full HCLG.fst graph
    subprocess.check_output(['./mkgraph.sh',
                     os.path.join(lang_model_dir, 'langdir'),
                     os.path.join(lang_model_dir, 'modeldir'),
                     os.path.join(lang_model_dir, 'graphdir')],
                    env=ENV, cwd=MKGRAPH_WD)

    # Return the language model directory
    return lang_model_dir

if __name__=='__main__':
    import sys
    getLanguageModel(open(sys.argv[1]).read())
