# coding=utf-8
import re

def tokenize(text):
    '''Split the text into TextTokens (distinct from the Tokens in
    alignment.py) by breaking on whitespace. Apostrophes and fancy
    unicode apostrophes are preserved.'''

    if type(text) != unicode:
        text = text.decode('utf-8')

    text_tokens = []
    for match in re.finditer(ur'(\w|\’\w|\'\w)+', text, re.UNICODE):
        start, end = match.span()
        text = match.group().encode('utf-8')
        text_tokens.append({
            "characterOffsetStart": start, # as unicode codepoint offset
            "characterOffsetEnd": end, # as unicode codepoint offset
            "text": text,
        })

    return text_tokens
