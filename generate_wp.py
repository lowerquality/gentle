# Take a transcript, and generate an APRA-style word-pair text file, in the style of
# https://catalog.ldc.upenn.edu/docs/LDC93S3B/disc_1/doc/wp_gram.txt
#
# Unlike the 1987 BBN example, we remove SENTENCE-END and make everything lowercase.

"""
 * A symbol '>' before a word in the list below signifies that the word is in
 * the first position of the bigram.
 * The sequence of words that immediately follow a bigram initial word
 * constitute the words allowed in the second position of the bigram.
 *
 * A distinguished symbol, 'SENTENCE-END', has been added to the lexicon
 * for the purpose of this specification and for computing the perplexity of 
 * the resulting language model.
 * Note that all words which follow the symbol, '>SENTENCE-END',
 * are the words which can occur at the begining of sentences.
 * Similarly, all words which contain the symbol, 'SENTENCE-END', in their
 * lists of allowable succeeding words constitute the words which can occur
 * at the end of sentences.
 * For this task domain, their are 181 legal sentence initial words and
 * 605 legal sentence final words.
"""

import sys
import re

def generate_wordpair(words_file, transcript_file, output_file):
    # XXX: If we refactored as a class, we could avoid repeatedly
    # loading the vocabulary
    vocabulary = set([X.split(' ')[0] for X in open(words_file).read().split('\n')])

    # Despite ARPA being all-caps, we may need lowercase.
    transcript = open(transcript_file).read().lower()

    # Turn hyphens into spaces
    transcript = transcript.replace('-', ' ')

    # Get rid of all punctuation except for periods and spaces
    # XXX: getting rid of periods
    transcript = re.sub(r'[^a-z\s\']', '', transcript)

    # # Replace periods with the SENTENCE-END sentinel
    # transcript = transcript.replace(".", " . ")

    word_sequence = [X.strip() for X in transcript.split() if len(X.strip()) > 0 and not X.startswith("'")]

    # We need to limit to words within a vocabulary
    word_sequence = [X if X in vocabulary else '[oov]' for X in word_sequence]
    return wordpair_from_word_sequence(word_sequence, output_file)

def wordpair_from_word_sequence(word_sequence, output_file):
    word_sequence = ['[oov]', '[oov]'] + word_sequence + ['[oov]']
    print word_sequence

    # Create a bigram mapping
    bigram = {}
    prev_word = word_sequence[0]
    for word in word_sequence[1:]:
        bigram.setdefault(prev_word, set()).add(word)
        prev_word = word

    # Dump bigram in ARPA wp format thing
    outf = open(output_file, 'w')
    for key in sorted(bigram.keys()):
        outf.write(">%s\n" % (key))
        for word in sorted(bigram[key]):
            outf.write(" %s\n" % (word))

    outf.close()


if __name__=='__main__':

    USAGE = "python generate_wp.py WORDS.TXT TRANSCRIPT OUTPUT_FILE"
    if len(sys.argv) != 4:
        print USAGE
        sys.exit(1)

    WORDS_FILE = sys.argv[1]
    TRANSCRIPT_FILE = sys.argv[2]
    OUTPUT_FILE = sys.argv[3]

    generate_wordpair(WORDS_FILE, TRANSCRIPT_FILE, OUTPUT_FILE)
