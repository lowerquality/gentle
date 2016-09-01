import gentle
import json
import logging
import logging.handlers
import sys

from helpers import *

class TestFullTranscriber:

    def test_harvard30_s01(self, request):
        name = "harvard-sentences-list30-s01"
        audiofile = input_path(name + ".mp3")
        resultfile = result_path("full-" + name + ".json")

        expected = gentle.Transcription.from_jsonfile(resultfile)

        resources = gentle.Resources()
        transcriber = gentle.FullTranscriber(resources)

        assert transcriber.available # verify language model is loaded

        with gentle.resampled(audiofile) as wavfile:
            result = transcriber.transcribe(wavfile)

        assert result == expected
