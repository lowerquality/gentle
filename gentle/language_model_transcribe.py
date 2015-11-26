import csv
import logging
import os
import json
import os
import shutil
import sys

import diff_align
from paths import get_resource
import language_model
import metasentence
import standard_kaldi

def lm_transcribe(audio_f, transcript, proto_langdir, nnet_dir,
                  partial_cb=None, partial_kwargs={}):

    if len(transcript.strip()) == 0:
        # Fall back on normal transcription if no transcript is provided
        logging.info("Falling back on normal transcription")
        return _normal_transcribe(audio_f, proto_langdir, nnet_dir, partial_cb, partial_kwargs)
    
    vocab_path = os.path.join(proto_langdir, "graphdir/words.txt")
    vocab = metasentence.load_vocabulary(vocab_path)

    ms = metasentence.MetaSentence(transcript, vocab)

    ks = ms.get_kaldi_sequence()

    gen_hclg_filename = language_model.make_bigram_language_model(ks, proto_langdir)
    try:
        k = standard_kaldi.Kaldi(nnet_dir, gen_hclg_filename, proto_langdir)

        trans = standard_kaldi.transcribe(k, audio_f,
                                          partial_results_cb=partial_cb,
                                          partial_results_kwargs=partial_kwargs)

        ret = diff_align.align(trans["words"], ms)
    finally:
        os.unlink(gen_hclg_filename)

    return {
        "transcript": transcript,
        "words": ret
    }

def _normal_transcribe(audio_f, proto_langdir, nnet_dir, partial_cb, partial_kwargs):
    hclg_path = get_resource("data/graph/HCLG.fst")
    if not os.path.exists(hclg_path):
        logging.warn("No general-purpose language model available")
        return {"transcript": "", "words": []}
    
    k = standard_kaldi.Kaldi(nnet_dir, hclg_path, proto_langdir)
    trans = standard_kaldi.transcribe(k, audio_f,
                                      partial_results_cb=partial_cb,
                                      partial_results_kwargs=partial_kwargs)
    # Spoof the `diff_align` output format
    transcript = ""
    words = []

    for t_wd in trans["words"]:
        wd = {
            "case": "success",
            "startOffset": len(transcript),
            "endOffset": len(transcript) + len(t_wd["word"]),
            "word": t_wd["word"],
            "alignedWord": t_wd["word"],
            "phones": t_wd["phones"],
            "start": t_wd["start"],
            "end": t_wd["start"] + t_wd["duration"]}
        words.append(wd)

        transcript += wd["word"] + " "

    return {
        "transcript": transcript,
        "words": words
    }


def write_csv(alignment, outf):
    w = csv.writer(outf)
    w.writerows(
        [ [X["word"], X.get("alignedWord"), X.get("start"), X.get("end")] for X in alignment["words"] if X.get("case") in ("success", "not-found-in-audio")])

if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Align a transcript to audio by generating a new language model.')
    parser.add_argument('--proto_langdir', default="PROTO_LANGDIR",
                       help='path to the prototype language directory')
    parser.add_argument('--nnet_dir', default="data/nnet_a_gpu_online",
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
    
