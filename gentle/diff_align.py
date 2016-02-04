import difflib
import json
import os
import sys

import language_model
import standard_kaldi

# TODO(maxhawkins): try using the (apparently-superior) time-mediated dynamic
# programming algorithm used in sclite's alignment process:
# http://www1.icsi.berkeley.edu/Speech/docs/sctk-1.2/sclite.htm#time-mediated
def align(hypothesis, reference):
    '''Use the diff algorithm to align the words recognized by Kaldi
    to the words in the (tokenized) transcript.
    
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
            source = reference[b]['source']

        if op == 'equal':
            out_tokens.append({
                "case": "success",
                "source": source,
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
                "source": source,
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
    import text
    from vocabulary import Vocabulary

    TEXT_FILE = sys.argv[1]
    JSON_FILE = sys.argv[2]
    OUTPUT_FILE = sys.argv[3]

    vocab = Vocabulary.from_file('data/graph/words.txt')

    text_tokens = text.tokenize(open(TEXT_FILE).read())
    # TODO(maxhawkins): de-dupe. this code is duplicated in language_model_transcribe.py
    reference_words = [vocab.normalize(token['text']) for token in text_tokens]
    reference = []
    for word, token in zip(reference_words, text_tokens):
        reference.append({
            'alignedWord': word,
            'source': token,
        })

    hypothesis = json.load(open(JSON_FILE))['tokens']

    out = align(hypothesis, ms)
    
    json.dump(out, open(OUTPUT_FILE, 'w'), indent=2)
