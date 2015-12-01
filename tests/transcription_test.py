from gentle.transcription import to_csv, to_json

from nose.tools import assert_equals

def test_to_json():
	tests = [
		[{"words": []}, '{"words": []}', 'empty'],
		# TODO(maxhawkins): add more
	]
	for test in tests:
		input, want, name = test
		got = to_json(input)
		assert_equals(want, got)	

def test_to_csv():
	tests = [
		[{"words": []}, '', 'empty'],
		[
			{
				"words": [
					{"case": "success", "word": "A", "alignedWord": "a", "start": 0, "end": 1},
				]
			},
			'A,a,0,1\r\n',
			'single word',
		],
		[
			{
				"words": [
					{"case": "success", "word": "A", "alignedWord": "a", "start": 0, "end": 1},
					{"case": "not-found-in-audio", "word": "B", "alignedWord": "b", "start": 2, "end": 3},
				]
			},
			'A,a,0,1\r\nB,b,2,3\r\n',
			'multi-word',
		],
		[
			{
				"words": [
					{"case": "not-found-in-audio", "word": "A", "alignedWord": "a", "start": 0, "end": 1},
				]
			},
			'A,a,0,1\r\n',
			'not found in audio',
		],
		[
			{
				"words": [
					{"case": "not-found-in-transcript", "word": "A", "alignedWord": "a", "start": 0, "end": 1},
				]
			},
			'',
			'not found in transcript',
		],
	]
	for test in tests:
		input, want, name = test
		got = to_csv(input)
		assert_equals(want, got)
