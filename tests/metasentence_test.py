# -*- coding: utf-8 -*-
from nose.tools import assert_equals

from gentle.metasentence import kaldi_normalize

def test_kaldi_normalization():
	vocab = [
		'test',
		'art',
		'related',
		'ad-hoc'
	]

	tests = [
		['', [], 'preserves empty'],
		['TEST', ['test'], 'makes lower case'],
		['art-related', ['art', 'related'], 'splits hyphenated words'],
		['test—art', ['test', 'art'], 'removes em dashes'],
		['art!!', ['art'], 'removes punctuation'],
		['art\ntest', ['art', 'test'], 'splits newlines'],
		['test\n', ['test'], 'ignores trailing newlines'],
		['unknown', ['[oov]'], 'removes oov words'],
		['ad-hoc', ['ad-hoc'], 'preserved in-vocab dashed words'],
		# ['1', ['one'], 'spells out numbers']
	]

	for test in tests:
		input, want, name = test
		got = kaldi_normalize(input, vocab)
		assert_equals(got, want)
