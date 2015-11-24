import metasentence
import language_model
import standard_kaldi

import difflib

import json
import os
import sys

def align(alignment, ms):

    # Compute an diff to turn the transcription results into the original sequence
    a = [X["word"] for X in alignment]
    b = ms.get_matched_kaldi_sequence()

    display_seq = ms.get_display_sequence()
    txt_offsets = ms.get_text_offsets()

    s = difflib.SequenceMatcher(a=a, b=b)

    out = []
    for opcode in s.get_opcodes():
        code, a_start, a_end, b_start, b_end = opcode

        if code == 'equal':
            for idx in range(a_end - a_start):
                start_offset, end_offset = txt_offsets[b_start + idx]
                out.append({
                    "case": "success",
                    "startOffset": start_offset,
                    "endOffset": end_offset,
                    "word": display_seq[b_start + idx],
                    "alignedWord": a[a_start + idx],
                    "phones": alignment[a_start + idx]["phones"],
                    "start": alignment[a_start + idx]["start"],
                    "end": alignment[a_start + idx]["start"] + alignment[a_start + idx]["duration"]})
        elif code in ['insert', 'replace']:
            # Could not align.
            for idx in range(b_end - b_start):
                start_offset, end_offset = txt_offsets[b_start + idx]
                out.append({
                    "case": "not-found-in-audio",
                    "startOffset": start_offset,
                    "endOffset": end_offset,
                    "word": display_seq[b_start + idx]})
            if code == 'replace':
                for idx in range(a_end - a_start):
                    out.append({
                        "case": "not-found-in-transcript",
                        "alignedWord": a[a_start + idx],
                        "phones": alignment[a_start + idx]["phones"],                        
                        "start": alignment[a_start + idx]["start"],
                        "end": alignment[a_start + idx]["start"] + alignment[a_start + idx]["duration"]})
        elif code == 'delete':
            for idx in range(a_end - a_start):
                out.append({
                    "case": "not-found-in-transcript",
                    "alignedWord": a[a_start + idx],
                    "phones": alignment[a_start + idx]["phones"],
                    "start": alignment[a_start + idx]["start"],
                    "end": alignment[a_start + idx]["start"] + alignment[a_start + idx]["duration"]})
    return out


if __name__=='__main__':
    TEXT_FILE = sys.argv[1]
    JSON_FILE = sys.argv[2]
    OUTPUT_FILE = sys.argv[3]

    vocab = metasentence.load_vocabulary('data/graph/words.txt')

    ms = metasentence.MetaSentence(open(TEXT_FILE).read(), vocab)
    alignment = json.load(open(JSON_FILE))['words']

    out = align(alignment, ms)
    
    json.dump(out, open(OUTPUT_FILE, 'w'), indent=2)
