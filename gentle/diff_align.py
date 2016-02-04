import difflib
import json
import os
import sys

import metasentence
import language_model
import standard_kaldi

# TODO(maxhawkins): try using the (apparently-superior) time-mediated dynamic
# programming algorithm used in sclite's alignment process:
# http://www1.icsi.berkeley.edu/Speech/docs/sctk-1.2/sclite.htm#time-mediated
def align(hypothesis, reference):
    '''Use the diff algorithm to align the words recognized by Kaldi
    to the words in the transcript (tokenized by MetaSentence).
    
    The output combines information about the timing and alignment of
    correctly-aligned words as well as words that Kaldi failed to recognize
    and extra words not found in the original transcript.
    '''
    hypothesis_words = [token['alignedWord'] for token in hypothesis]
    reference_words = [token['alignedWord'] for token in reference]

    out_tokens = []
    for op, a, b in word_diff(hypothesis_words, reference_words):
        if a < len(hypothesis):
            word = hypothesis[a]['alignedWord']
            time = hypothesis[a]['time']
            phones = hypothesis[a]['phones']
        if b < len(reference):
            source_text = reference[b]['word']
            start_offset = reference[b]['startOffset']
            end_offset = reference[b]['endOffset']

        if op == 'equal':
            out_tokens.append({
                "case": "success",
                "startOffset": start_offset,
                "endOffset": end_offset,
                "word": source_text,
                "alignedWord": word,
                "phones": phones,
                "time": time,
            })
        elif op == 'delete':
            out_tokens.append({
                "case": "not-found-in-transcript",
                "alignedWord": word,
                "phones": phones,
                "time": time,
            })
        elif op in 'insert':
            out_tokens.append({
                "case": "not-found-in-audio",
                "startOffset": start_offset,
                "endOffset": end_offset,
                "word": source_text,
            })
    return out_tokens

def word_diff(a, b):
    '''Like difflib.SequenceMatcher but it only compares one word
    at a time. Returns an iterator whose elements are like
    (operation, index in a, index in b)'''
    matcher = difflib.SequenceMatcher(a=a, b=b)
    for op, a_idx, _, b_idx, _ in by_word(matcher.get_opcodes()):
        yield (op, a_idx, b_idx)

def without_replace(opcodes):
    '''Substitute insert/delete pairs for replace opcodes in
    difflib.SequenceMatcher.get_opcodes() output'''
    for op, s1, e1, s2, e2 in opcodes:
        if op == 'replace':
            yield ('delete', s1, e1, s2, s2)
            yield ('insert', e1, e1, s2, e2)
        else:
            yield (op, s1, e1, s2, e2)

def by_word(opcodes):
    '''Take difflib.SequenceMatcher.get_opcodes() output and
    return an equivalent opcode sequence that only modifies
    one word at a time'''
    for op, s1, e1, s2, e2 in opcodes:
        if op == 'delete':
            for i in range(s1, e1):
                yield (op, i, i+1, s2, s2)
        elif op == 'insert':
            for i in range(s2, e2):
                yield (op, s1, s1, i, i+1)
        else:
            for i1, i2 in zip(range(s1, e1), range(s2, e2)):
                yield (op, i1, i1 + 1, i2, i2 + 1)

if __name__=='__main__':
    TEXT_FILE = sys.argv[1]
    JSON_FILE = sys.argv[2]
    OUTPUT_FILE = sys.argv[3]

    with open('data/graph/words.txt') as f:
        vocab = metasentence.load_vocabulary(f)

    ms = metasentence.MetaSentence(open(TEXT_FILE).read(), vocab)
    hypothesis = json.load(open(JSON_FILE))['tokens']

    out = align(hypothesis, ms)
    
    json.dump(out, open(OUTPUT_FILE, 'w'), indent=2)
