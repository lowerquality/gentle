import metasentence
import language_model
import standard_kaldi

import diff_align

import json
import os
import sys


vocab = metasentence.load_vocabulary('PROTO_LANGDIR/graphdir/words.txt')

def lm_transcribe(audio_f, text_f):

    ms = metasentence.MetaSentence(open(text_f).read(), vocab)
    model_dir = language_model.getLanguageModel(ms.get_kaldi_sequence())

    print 'generated model', model_dir

    k = standard_kaldi.Kaldi(os.path.join(model_dir, 'graphdir', 'HCLG.fst'))

    trans = standard_kaldi.transcribe(k, audio_f)

    ret = diff_align.align(trans["words"], ms)

    return ret

if __name__=='__main__':
    AUDIO_FILE = sys.argv[1]
    TEXT_FILE = sys.argv[2]
    OUTPUT_FILE = sys.argv[3]

    ret = lm_transcribe(AUDIO_FILE, TEXT_FILE)
    json.dump(ret, open(OUTPUT_FILE, 'w'), indent=2)
    
