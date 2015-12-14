# -*- coding: utf-8 -*-

import json
import os
import unittest

from nose.tools import assert_greater, assert_less

from gentle.language_model_transcribe import lm_transcribe
from gentle.alignment_score import alignment_score

@unittest.skipIf(os.environ.get('SHORT') == 'true', 'skipping for short test')
def test_e2e():
	with open("tests/data/lucier_golden.json") as f:
		golden = json.load(f)
	with open("tests/data/lucier.txt") as f:
		transcript = f.read()
	ret = lm_transcribe(
		"tests/data/lucier.mp3",
		transcript,
		"PROTO_LANGDIR",
		"data/nnet_a_gpu_online")
	
	score = alignment_score(golden['words'], ret['words'])
	assert_greater(score['correct'], 0.85)
	assert_less(score['error'], 0.35)
