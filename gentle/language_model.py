from generate_wp import language_model_from_word_sequence
import os
import subprocess
import sys
import tempfile

MKGRAPH_PATH = "./mkgraph"

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
    getLanguageModel(open(sys.argv[1]).read())
