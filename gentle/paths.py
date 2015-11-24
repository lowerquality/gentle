import os
import glob
import shutil
import sys

if hasattr(sys, "frozen") and sys.frozen == "macosx_app":
    print 'FROZEN!'
else:
    print 'NOT FROZEN!'

def get_binary(name):
    if hasattr(sys, "frozen") and sys.frozen == "macosx_app":
        return "./../Resources/%s" % (name)
    elif os.path.exists(name):
        return "./%s" % (name)
    else:
        return name

def get_resource(path):
    if hasattr(sys, "frozen") and sys.frozen == "macosx_app":
        return "../Resources/%s" % (path)
    else:
        return path

def get_datadir(path):
    if hasattr(sys, "frozen") and sys.frozen == "macosx_app":
        return os.path.join(os.environ['HOME'], '.gentle', path)
    else:
        return path


        
def ensure_kaldi_config(src, dst):
    """Mangle the paths in the Kaldi configuration from a pristine `src`
    to an arbitrary destination"""
    # XXX: this is hideous.

    print 'ensure_kaldi_config', src, dst

    for dirname in ['conf', 'ivector_extractor']:
        if not os.path.exists(os.path.join(dst, dirname)):
            shutil.copytree(os.path.join(src, dirname),
                            os.path.join(dst, dirname))
            
            for fpath in glob.glob(os.path.join(dst, dirname, '*.conf')):
                print 'config file', fpath
                txt = open(fpath).read()
                txt = txt.replace('/Users/rmo/data/speech-data/nnet_a_gpu_online', dst)
                open(fpath, 'w').write(txt)
