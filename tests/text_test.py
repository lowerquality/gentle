# -*- coding: utf-8 -*-
from nose.tools import assert_equals

from gentle.text import tokenize

def test_tokenize():
	tests = [
		['', [], 'blank'],
		[' ', [], 'just space'],
		['test', [(0, 4)], 'single token'],
		['  test', [(2, 6)], 'leading space'],
		['test  ', [(0, 4)], 'trailing space'],
		['test test', [(0, 4), (5, 9)], 'two tokens'],
		['test\ntest', [(0, 4), (5, 9)], 'newline delimiter'],
		['\n\ntest', [(2, 6)], 'leading newlines'],
		['test-test', [(0, 4), (5, 9)], 'hyphenated'],
		['test—test', [(0, 4), (5, 9)], 'em-space'],
		['test!!', [(0, 4)], 'trailing punctiation'],
		['duchamp\'s', [(0, 9)], 'preserves apostrope'],
		['duchamp’s', [(0, 9)], 'preserves fancy apostrope'],
		['‘test’', [(1, 5)], 'ignores fancy single quote'],
		['test’ ', [(0, 4)], 'ignores fancy single quote'],
		['¡¡ωσω!!', [(2, 5)], 'fancy text'],
	]

	for test in tests:
		input, want, name = test
		tokens = tokenize(input)

		got = []
		for token in tokens:
			got.append((
				token['characterOffsetStart'],
				token['characterOffsetEnd'],
			))
		assert_equals(got, want)
