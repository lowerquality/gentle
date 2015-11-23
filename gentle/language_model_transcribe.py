import csv
import os
import json
import os
import shutil
import sys

import diff_align
import language_model
import metasentence
import standard_kaldi

def lm_transcribe(audio_f, transcript, proto_langdir, nnet_dir):
    vocab_path = os.path.join(proto_langdir, "graphdir/words.txt")
    vocab = metasentence.load_vocabulary(vocab_path)

    ms = metasentence.MetaSentence(transcript, vocab)
    gen_model_dir = language_model.get_language_model(ms.get_kaldi_sequence(), proto_langdir)

    sys.stderr.write('generated model %s\n' % gen_model_dir)

    try:
        gen_hclg_path = os.path.join(gen_model_dir, 'graphdir', 'HCLG.fst')
        k = standard_kaldi.Kaldi(nnet_dir, gen_hclg_path, proto_langdir)

        trans = standard_kaldi.transcribe(k, audio_f)

        ret = diff_align.align(trans["words"], ms)
    finally:
        shutil.rmtree(gen_model_dir)

    return ret

def write_csv(alignment, outf):
    w = csv.writer(outf)
    w.writerows(
        [ [X["word"], X.get("alignedWord"), X.get("start"), X.get("end")] for X in alignment if X.get("case") in ("success", "not-found-in-audio")])

if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Align a transcript to audio by generating a new language model.')
    parser.add_argument('--proto_langdir', default="PROTO_LANGDIR",
                       help='path to the prototype language directory')
    parser.add_argument('--nnet_dir', default="data",
                       help='path to the kaldi neural net model directory')
    parser.add_argument('audio_file', help='input audio file in any format supported by FFMPEG')
    parser.add_argument('input_file', type=argparse.FileType('r'),
                        help='input transcript as plain text or json')
    parser.add_argument('output_file', type=argparse.FileType('w'),
                       help='output file for aligned transcript (json or csv)')

    args = parser.parse_args()

    if args.input_file.name.endswith('.json'):
        intxt = ''
        for line in json.load(open(args.input_file)):
            intxt += line['line'] + '\n\n'
    else:
        intxt = args.input_file.read()

    ret = lm_transcribe(args.audio_file, intxt, args.proto_langdir, args.nnet_dir)
    if args.output_file.name.endswith('.csv'):
        write_csv(ret, args.output_file)
    else:
        json.dump({"words": ret}, args.output_file, indent=2)
    
