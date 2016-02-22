import csv
import logging
import os
import json
import os
import shutil
import sys

from paths import get_resource
import diff_align
import language_model
import metasentence
import standard_kaldi
import transcription

def lm_transcribe(audio_f, transcript, proto_langdir, nnet_dir):
    ret = None
    for ret in lm_transcribe_progress(audio_f, transcript, proto_langdir, nnet_dir):
        pass
    return ret

def lm_transcribe_progress(audio_f, transcript, proto_langdir, nnet_dir):

    if len(transcript.strip()) == 0:
        # Fall back on normal transcription if no transcript is provided
        logging.info("Falling back on normal transcription")
        for ret in _normal_transcribe(audio_f, proto_langdir, nnet_dir):
            yield ret
        return
    
    vocab_path = os.path.join(proto_langdir, "graphdir/words.txt")
    with open(vocab_path) as f:
        vocab = metasentence.load_vocabulary(f)

    ms = metasentence.MetaSentence(transcript, vocab)

    ks = ms.get_kaldi_sequence()

    gen_hclg_filename = language_model.make_bigram_language_model(ks, proto_langdir)
    k = None
    try:
        k = standard_kaldi.Kaldi(nnet_dir, gen_hclg_filename, proto_langdir)

        ret = None
        for trans in k.transcribe_progress(audio_f):
            ret = diff_align.align(trans["words"], ms)
            yield {
                "transcript": transcript,
                "words": ret,
            }
    finally:
        if k:
            k.stop()
        os.unlink(gen_hclg_filename)

def _normal_transcribe(audio_f, proto_langdir, nnet_dir):
    hclg_path = get_resource("data/graph/HCLG.fst")
    if not os.path.exists(hclg_path):
        logging.warn("No general-purpose language model available")
        yield {
            "transcript": "",
            "words": [],
        }

    k = standard_kaldi.Kaldi(nnet_dir, hclg_path, proto_langdir)
    for trans in k.transcribe_progress(audio_f, batch_size=5):
        # Spoof the `diff_align` output format
        transcript = ""
        words = []

        for t_wd in trans["words"]:
            word = {
                "case": "success",
                "startOffset": len(transcript),
                "endOffset": len(transcript) + len(t_wd["word"]),
                "word": t_wd["word"],
                "alignedWord": t_wd["word"],
                "phones": t_wd["phones"],
                "start": t_wd["start"],
                "end": t_wd["start"] + t_wd["duration"]}
            words.append(word)

            transcript += word["word"] + " "

        yield {
            "transcript": transcript,
            "words": words
        }
    k.stop()


if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Align a transcript to audio by generating a new language model.')
    parser.add_argument('--proto_langdir', default="PROTO_LANGDIR",
                       help='path to the prototype language directory')
    parser.add_argument('--nnet_dir', default="data/nnet_a_gpu_online",
                       help='path to the kaldi neural net model directory')
    parser.add_argument('--format', default="json", choices=["json", "csv", "ctm"],
                        help="the file output format, the output file has no extension")
    parser.add_argument('audio_file', help='input audio file in any format supported by FFMPEG')
    parser.add_argument('input_file', type=argparse.FileType('r'),
                        help='input transcript as plain text or json')
    parser.add_argument('output_file', type=argparse.FileType('w'),
                       help='output file for aligned transcript (json or csv)')

    args = parser.parse_args()

    if args.input_file.name.endswith('.json'):
        intxt = ''
        for line in json.load(args.input_file):
            intxt += line['line'] + '\n\n'
    else:
        intxt = args.input_file.read()

    outfile = args.output_file
    out_format = args.format
    if outfile.name.endswith('.csv'):
        out_format = 'csv'
    elif outfile.name.endswith('.json'):
        out_format = 'json'
    elif outfile.name.endswith('.ctm'):
        out_format = 'ctm'

    ret = None
    for ret in lm_transcribe_progress(args.audio_file, intxt, args.proto_langdir, args.nnet_dir):
        sys.stderr.write('.')
    sys.stderr.write('\n')
    
    if out_format == 'csv':
        formatted = transcription.to_csv(ret)
    elif out_format == 'ctm':
        formatted = transcription.to_ctm(ret)
    else:
        formatted = transcription.to_json(ret, indent=2)
    outfile.write(formatted)
    
