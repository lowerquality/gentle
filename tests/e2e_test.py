# -*- coding: utf-8 -*-

from nose.tools import assert_equals
import json

from gentle.language_model_transcribe import lm_transcribe

def test_metasentence_tokenization():
	with open("tests/data/lucier_golden.json") as f:
		golden = json.load(f)
	with open("tests/data/lucier.txt") as f:
		transcript = f.read()
	ret = lm_transcribe(
		"tests/data/lucier.mp3",
		transcript,
		"PROTO_LANGDIR",
		"data/nnet_a_gpu_online")
	assert_equals(golden, ret)
