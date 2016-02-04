# -*- coding: utf-8 -*-
from nose.tools import assert_equals

from gentle.vocabulary import Vocabulary, load_word_file

def test_load_word_file():
	tests = [
		[['<eps> 0'], set(['<eps>'])],
		[['<eps> 0', ''], set(['<eps>'])],
		[['a 66', 'zulu 124944'], set(['a', 'zulu'])],
	]
	for test in tests:
		input, want = test
		got = load_word_file(input)
		assert_equals(got, want)

def test_vocabulary_normalize():
	vocab = Vocabulary([
		'test',
		'duchamp\'s',
	])

	tests = [
		['', '', 'preserves empty'],
		['TEST', 'test', 'makes lower case'],
		['unknown', '[oov]', 'removes oov words'],
		['duchamp’s', 'duchamp\'s', 'simplifies fancy quotes'],
	]

	for test in tests:
		input, want, name = test
		got = vocab.normalize(input)
		assert_equals(got, want)
