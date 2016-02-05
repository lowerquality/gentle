import csv
import logging
import os
import json
import os
import shutil
import sys

from paths import get_resource
from vocabulary import Vocabulary
import text
import diff_align
import language_model
import standard_kaldi
import alignment

def lm_transcribe(audio_f, transcript, proto_langdir, nnet_dir):
    align = None
    for align in lm_transcribe_progress(audio_f, transcript, proto_langdir, nnet_dir):
        pass
    return align

def lm_transcribe_progress(audio_f, transcript, proto_langdir, nnet_dir):

    if len(transcript.strip()) == 0:
        # Fall back on normal transcription if no transcript is provided
        logging.info("Falling back on normal transcription")
        for align in _normal_transcribe(audio_f, proto_langdir, nnet_dir):
            yield align
        return
    
    vocab_path = os.path.join(proto_langdir, "graphdir/words.txt")
    vocab = Vocabulary.from_file(vocab_path)

    text_tokens = text.tokenize(transcript)
    reference_words = [vocab.normalize(token['text']) for token in text_tokens]
    reference = []
    for word, token in zip(reference_words, text_tokens):
        reference.append({
            'alignedWord': word,
            'source': token,
        })

    gen_hclg_filename = language_model.make_bigram_language_model(reference_words, proto_langdir)
    try:
        k = standard_kaldi.Kaldi(nnet_dir, gen_hclg_filename, proto_langdir)

        for trans in k.transcribe_progress(audio_f):
            hypothesis = trans["tokens"]
            aligned_tokens = diff_align.align(hypothesis, reference)
            yield {
                "transcript": transcript,
                "tokens": aligned_tokens,
            }
    finally:
        k.stop()
        os.unlink(gen_hclg_filename)

def _normal_transcribe(audio_f, proto_langdir, nnet_dir):
    hclg_path = get_resource("data/graph/HCLG.fst")
    if not os.path.exists(hclg_path):
        logging.warn("No general-purpose language model available")
        yield {
            "transcript": "",
            "tokens": [],
        }

    k = standard_kaldi.Kaldi(nnet_dir, hclg_path, proto_langdir)
    for trans in k.transcribe_progress(audio_f, batch_size=5):
        # Spoof the `diff_align` output format
        transcript = ""
        tokens = []

        for trans_token in trans["tokens"]:

            word = trans_token['alignedWord']
            source = {
                "text": word,
                "characterOffsetStart": len(transcript),
                "characterOffsetEnd": len(transcript) + len(word),
            }
            token = {
                "case": "success",
                "alignedWord": word,
                "source": source,
                "phones": trans_token["phones"],
                "time": trans_token['time'],
            }
            tokens.append(token)

            transcript += word + " "

        yield {
            "transcript": transcript,
            "tokens": tokens
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
                       help='output file for the alignment (json or csv)')

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

    align = None
    for align in lm_transcribe_progress(args.audio_file, intxt, args.proto_langdir, args.nnet_dir):
        sys.stderr.write('.')
    sys.stderr.write('\n')
    
    if out_format == 'csv':
        formatted = alignment.to_csv(align)
    elif out_format == 'ctm':
        formatted = alignment.to_ctm(align)
    else:
        formatted = alignment.to_json(align, indent=2)
    outfile.write(formatted)
    
