from nose.tools import assert_equals, raises
import json

from gentle.alignment_score import alignment_score

@raises(ValueError)
def test_no_ref_text():
	alignment_score([], [])

def test_golden_master_identity():
	with open("tests/data/lucier_golden.json") as f:
		golden = json.load(f)['words']
	got = alignment_score(golden, golden)
	want = {
		'inserted': 0.0,
		'correct': 1.0,
		'deleted': 0.0,
		'substituted': 0.0,
		'error': 0.0,
	}
	assert_equals(got, want)


def test_alignment_score():
	tests = [
		[
			[{'case': 'success', 'alignedWord': 'hello', 'start': 0, 'end': 1}],
			[{'case': 'success', 'alignedWord': 'hello', 'start': 0, 'end': 1}],
			{
				'inserted': 0.0,
				'correct': 1.0,
				'deleted': 0.0,
				'substituted': 0.0,
				'error': 0.0,
			},
			'one correct',
		],
		[
			[{'case': 'success', 'alignedWord': 'one', 'start': 0, 'end': 1}, {'case': 'success', 'alignedWord': 'two', 'start': 2, 'end': 3}],
			[{'case': 'success', 'alignedWord': 'one', 'start': 0, 'end': 1}, {'case': 'success', 'alignedWord': 'two', 'start': 2, 'end': 3}],
			{
				'inserted': 0.0,
				'correct': 1.0,
				'deleted': 0.0,
				'substituted': 0.0,
				'error': 0.0,
			},
			'two correct',
		],
		[
			[{'case': 'success', 'alignedWord': 'hello', 'start': 0, 'end': 1}],
			[{'case': 'success', 'alignedWord': 'hello', 'start': 0, 'end': 1}, {'case': 'success', 'alignedWord': 'hello', 'start': 0, 'end': 1}],
			{
				'inserted': 0.0,
				'correct': 0.5,
				'deleted': 0.5,
				'substituted': 0.0,
				'error': 0.5,
			},
			'one deleted, one correct',
		],
		[
			[{'case': 'success', 'alignedWord': 'hello', 'start': 0, 'end': 1}, {'case': 'not-found-in-transcript', 'alignedWord': 'two', 'start': 2, 'end': 3}],
			[{'case': 'success', 'alignedWord': 'hello', 'start': 0, 'end': 1}],
			{
				'inserted': 1.0,
				'correct': 1.0,
				'deleted': 0.0,
				'substituted': 0.0,
				'error': 1.0,
			},
			'one inserted',
		],
		[
			[{'case': 'success', 'alignedWord': 'hello', 'start': 0, 'end': 1}, {'case': 'not-found-in-transcript', 'alignedWord': 'two', 'start': 2, 'end': 3}, {'case': 'not-found-in-transcript', 'alignedWord': 'three', 'start': 4, 'end': 5}],
			[{'case': 'success', 'alignedWord': 'hello', 'start': 0, 'end': 1}],
			{
				'inserted': 2.0,
				'correct': 1.0,
				'deleted': 0.0,
				'substituted': 0.0,
				'error': 2.0,
			},
			'two inserted',
		],
		[
			[],
			[{'case': 'success', 'alignedWord': 'hello', 'start': 0, 'end': 1}],
			{
				'inserted': 0.0,
				'correct': 0.0,
				'deleted': 1.0,
				'substituted': 0.0,
				'error': 1.0,
			},
			'one deleted',
		],
		[
			[],
			[{'case': 'success', 'alignedWord': 'one', 'start': 0, 'end': 1}, {'case': 'success', 'alignedWord': 'two', 'start': 0, 'end': 1}],
			{
				'inserted': 0.0,
				'correct': 0.0,
				'deleted': 1.0,
				'substituted': 0.0,
				'error': 1.0,
			},
			'two deleted',
		],
		[
			[{'case': 'not-found-in-transcript', 'alignedWord': 'yes', 'start': 0, 'end': 1}],
			[{'case': 'success', 'alignedWord': 'no', 'start': 0, 'end': 1}],
			{
				'inserted': 0.0,
				'correct': 0.0,
				'deleted': 0.0,
				'substituted': 1.0,
				'error': 1.0,
			},
			'one substituted',
		],
		[
			[{'case': 'not-found-in-transcript', 'alignedWord': 'yes', 'start': 0, 'end': 1}, {'case': 'not-found-in-transcript', 'alignedWord': 'yes2', 'start': 2, 'end': 3}],
			[{'case': 'success', 'alignedWord': 'no', 'start': 0, 'end': 1}, {'case': 'success', 'alignedWord': 'no2', 'start': 2, 'end': 3}],
			{
				'inserted': 0.0,
				'correct': 0.0,
				'deleted': 0.0,
				'substituted': 1.0,
				'error': 1.0,
			},
			'two substituted',
		],
		[
			[{'case': 'success', 'alignedWord': 'hello', 'start': 0, 'end': 1}, {'case': 'not-found-in-audio', 'alignedWord': 'hello'}],
			[{'case': 'success', 'alignedWord': 'hello', 'start': 0, 'end': 1}],
			{
				'inserted': 0.0,
				'correct': 1.0,
				'deleted': 0.0,
				'substituted': 0.0,
				'error': 0.0,
			},
			'not found in audio',
		],
	]
	for hyp, ref, want, name in tests:
		got = alignment_score(hyp, ref)
		msg = "%s: wanted %r, got %r" % (name, want, got)
		assert_equals(got, want, msg)
