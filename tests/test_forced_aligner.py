import gentle
import logging
import logging.handlers
import sys

from helpers import *

class TestForcedAligner:

    def test_harvard30(self, tmpdir, request):
        name = "harvard-sentences-list30"
        transcript = input_data(name + ".txt")
        audiofile = input_path(name + ".mp3")
        expectedfile = expected_path("forced-" + name + ".json")
        resultfile = result_path("forced-" + name + ".json")

        expected = gentle.Transcription.from_jsonfile(expectedfile)
        assert transcript == expected.transcript # test data consistency check

        resources = gentle.Resources()
        aligner = gentle.ForcedAligner(resources, transcript)

        logger = logging.getLogger(request.node.name)
        handler = logging.handlers.MemoryHandler(sys.maxint)
        logger.addHandler(handler)
        logger.setLevel('INFO')

        with gentle.resampled(audiofile) as wavfile:
            result = aligner.transcribe(wavfile, logging=logger)

        log = [record.getMessage() for record in handler.buffer]

        with open(resultfile, "w") as fh:
            fh.write(result.to_json())

        assert result == expected
        assert "5 unaligned words (of 86)" in log
        assert "after 2nd pass: 0 unaligned words (of 86)" in log
