import os

from gentle import kaldi_queue
from gentle import transcription
from gentle.transcriber import MultiThreadedTranscriber
from gentle.transcription import Transcription

class FullTranscriber():

    def __init__(self, resources, nthreads=2):
        self.available = False
        if nthreads <= 0: return
        if not os.path.exists(resources.full_hclg_path): return

        queue = kaldi_queue.build(resources, nthreads=nthreads)
        self.mtt = MultiThreadedTranscriber(queue, nthreads=nthreads)
        self.available = True

    def transcribe(self, wavfile, progress_cb=None, logging=None):
        words, duration = self.mtt.transcribe(wavfile, progress_cb=progress_cb)
        return self.make_transcription_alignment(words)

    @staticmethod
    def make_transcription_alignment(trans):
        # Spoof the `diff_align` output format
        transcript = ""
        words = []
        for t_wd in trans:
            word = transcription.Word(
                case=transcription.Word.SUCCESS,
                startOffset=len(transcript),
                endOffset=len(transcript) + len(t_wd.word),
                word=t_wd.word,
                alignedWord=t_wd.word,
                phones=t_wd.phones,
                start=t_wd.start,
                end=t_wd.end)
            words.append(word)

            transcript += word.word + " "

        return Transcription(words=words, transcript=transcript)
