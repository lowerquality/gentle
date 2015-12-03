from nose.tools import assert_equals

from gentle.diff_align import without_replace, by_word

def test_by_word():
	tests = [
		[
			[('insert', 0, 0, 4, 6)],
			[('insert', 0, 0, 4, 5), ('insert', 0, 0, 5, 6)],
			'insert',
		],
		[
			[('delete', 2, 4, 9, 9)],
			[('delete', 2, 3, 9, 9), ('delete', 3, 4, 9, 9)],
			'delete',
		],
		[
			[('equal', 0, 2, 7, 9)],
			[('equal', 0, 1, 7, 8), ('equal', 1, 2, 8, 9)],
			'equal',
		],
		[
			[('replace', 0, 2, 6, 8)],
			[('replace', 0, 1, 6, 7), ('replace', 1, 2, 7, 8)],
			'replace',
		],
		[
			[],
			[],
			'empty',
		],
	]
	for input, want, name in tests:
		got = list(by_word(input))
		msg = "%s: got %r, want %r" % (name, got, want)
		assert_equals(got, want, msg)

def test_without_replace():
	tests = [
		[
			[('replace', 0, 1, 1, 2)],
			[('delete', 0, 1, 1, 1), ('insert', 1, 1, 1, 2)],
			'one replace',
		],
		[
			[('replace', 0, 1, 0, 1)],
			[('delete', 0, 1, 0, 0), ('insert', 1, 1, 0, 1)],
			'replace same',
		],
		[
			[('delete', 0, 1, 0, 0), ('insert', 0, 0, 0, 1), ('equal', 4, 5, 4, 5)],
			[('delete', 0, 1, 0, 0), ('insert', 0, 0, 0, 1), ('equal', 4, 5, 4, 5)],
			'Others preserved',
		],
		[
			[],
			[],
			'empty',
		],
	]
	for input, want, name in tests:
		got = list(without_replace(input))
		msg = "%s: got %r, want %r" % (name, got, want)
		assert_equals(got, want, msg)


