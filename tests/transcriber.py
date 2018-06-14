import os
import unittest

class Transcriber(unittest.TestCase):
    audio = 'examples/data/lucier.mp3'

    def test_resources(self):
        from gentle import Resources
        from gentle.util.paths import get_binary

        resources = Resources()
        k3 = get_binary("ext/k3")

        self.assertEqual(os.path.exists(resources.full_hclg_path), True)
        self.assertEqual(os.path.exists(self.audio), True)
        self.assertEqual(os.path.exists(k3), True)

    def test_transcriber(self):
        import subprocess
        from gentle import resampled, kaldi_queue, standard_kaldi, Resources
        from gentle.transcriber import MultiThreadedTranscriber

        standard_kaldi.STDERR = subprocess.STDOUT

        resources = Resources()
        k_queue = kaldi_queue.build(resources, 1)
        trans = MultiThreadedTranscriber(k_queue)

        with resampled(self.audio, 10.5, 2.5) as filename:
            words, duration = trans.transcribe(filename)
        self.assertEqual(words[0].word, "different")
