import os
import unittest

class Aligner(unittest.TestCase):
    audio = 'examples/data/lucier.mp3'
    transcript = "i am sitting in a room"

    def test_resources(self):
        from gentle import Resources
        from gentle.util.paths import get_binary

        resources = Resources()
        k3 = get_binary("ext/k3")
        model = get_binary("exp/tdnn_7b_chain_online/final.mdl" )       

        self.assertEqual(os.path.exists(self.audio), True)
        self.assertEqual(os.path.exists(k3), True)
        self.assertEqual(os.path.exists(model), True)

    def test_aligner(self):
        import subprocess
        from gentle import resampled, standard_kaldi, Resources
        from gentle.forced_aligner import ForcedAligner
        from gentle.transcription import Word

        standard_kaldi.STDERR = subprocess.STDOUT

        resources = Resources()
        align = ForcedAligner(resources, self.transcript, nthreads=1)

        with resampled(self.audio, 5.0, 5.0) as filename:
            transcription = align.transcribe(filename)
            words = transcription.words
        self.assertEqual(words[0].word, "i")
        self.assertEqual(words[1].word, "am")
        self.assertEqual(words[1].case, Word.SUCCESS)        
