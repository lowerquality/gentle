import metasentence
import language_model
import standard_kaldi

import diff_align

import json
import os
import sys


vocab = metasentence.load_vocabulary('PROTO_LANGDIR/graphdir/words.txt')

def lm_transcribe(audio_f, text_f, proto_langdir, nnet_dir):

    ms = metasentence.MetaSentence(open(text_f).read(), vocab)
    gen_model_dir = language_model.getLanguageModel(ms.get_kaldi_sequence())

    print 'generated model', gen_model_dir

    gen_hclg_path = os.path.join(gen_model_dir, 'graphdir', 'HCLG.fst')
    k = standard_kaldi.Kaldi(nnet_dir, gen_hclg_path, proto_langdir)

    trans = standard_kaldi.transcribe(k, audio_f)

    ret = diff_align.align(trans["words"], ms)

    return ret

if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Align a transcript to audio by generating a new language model.')
    parser.add_argument('audio_file', help='input audio file in any format supported by FFMPEG')
    parser.add_argument('text_file', help='input transcript as plain text')
    parser.add_argument('output_file', type=argparse.FileType('w'),
                       help='output json file for aligned transcript')
    parser.add_argument('--proto_langdir', default="PROTO_LANGDIR",
                       help='path to the prototype language directory')
    parser.add_argument('--nnet_dir', default="data",
                       help='path to the kaldi neural net model directory')

    args = parser.parse_args()

    ret = lm_transcribe(args.audio_file, args.text_file, args.proto_langdir, args.nnet_dir)
    json.dump(ret, args.output_file, indent=2)
    
