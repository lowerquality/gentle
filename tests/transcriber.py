import unittest


class Transcriber(unittest.TestCase):

    def test_transcriber(self):
        from gentle import resampled, kaldi_queue, standard_kaldi, Resources
        from gentle.transcriber import MultiThreadedTranscriber

        resources = Resources()
        k_queue = kaldi_queue.build(resources, 1)
        trans = MultiThreadedTranscriber(k_queue)

        with resampled('examples/data/lucier.mp3', 10.5, 2.5) as filename:
            words, duration = trans.transcribe(filename)
        self.assertEqual(words[0].word, "different")
