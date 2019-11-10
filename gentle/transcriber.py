import math
import logging
import wave

from gentle import transcription

from multiprocessing.pool import ThreadPool as Pool

class Transcriber:
    def __init__(self, kaldi_queue, chunk_len=20, overlap_t=2):
        self.chunk_len = chunk_len
        self.overlap_t = overlap_t if overlap_t < chunk_len else max(chunk_len - 1, 0)
        self.kaldi_queue = kaldi_queue

    def transcribe_chunk(self, wavfile, idx):
        wav_obj = wave.open(wavfile, 'rb')
        start_t = idx * (self.chunk_len - self.overlap_t)
        # Seek
        wav_obj.setpos(int(start_t * wav_obj.getframerate()))
        # Read frames
        buf = wav_obj.readframes(int(self.chunk_len * wav_obj.getframerate()))

        if len(buf) < 4000:
            logging.info('Short segment - ignored %d' % (idx))
            ret = []
        else:
            k = self.kaldi_queue.get()
            k.push_chunk(buf)
            ret = k.get_final()
            self.kaldi_queue.put(k)

        return {"start": start_t, "words": ret}

    def transcribe(self, wavfile, progress_cb=None):
        wav_obj = wave.open(wavfile, 'rb')
        duration = wav_obj.getnframes() / float(wav_obj.getframerate())
        n_chunks = int(math.ceil(duration / float(self.chunk_len - self.overlap_t)))

        chunks = []        
        for n in range(0, n_chunks):
            chunk = self.transcribe_chunk(wavfile, n)
            chunks.append(chunk)
            self.log_progress(len(chunks), n_chunks, chunk.get("words"), progress_cb)

        return self.combine_chunks(chunks, duration)

    def log_progress(self, x_chunks, n_chunks, ret, progress_cb):
        logging.info('%d/%d' % (x_chunks, n_chunks))
        if progress_cb is not None:
            progress_cb({"message": ' '.join([X['word'] for X in ret]),
                            "percent": x_chunks / float(n_chunks)})
        
    def combine_chunks(self, chunks, duration):
        chunks.sort(key=lambda x: x['start'])

        # Combine chunks
        words = []
        for c in chunks:
            chunk_start = c['start']
            chunk_end = chunk_start + self.chunk_len

            chunk_words = [transcription.Word(**wd).shift(time=chunk_start) for wd in c['words']]

            # At chunk boundary cut points the audio often contains part of a
            # word, which can get erroneously identified as one or more different
            # in-vocabulary words.  So discard one or more words near the cut points
            # (they'll be covered by the ovlerap anyway).
            #
            trim = min(0.25 * self.overlap_t, 0.5)
            if c is not chunks[0]:
                while len(chunk_words) > 1:
                    chunk_words.pop(0)
                    if chunk_words[0].end > chunk_start + trim:
                        break
            if c is not chunks[-1]:
                while len(chunk_words) > 1:
                    chunk_words.pop()
                    if chunk_words[-1].start < chunk_end - trim:
                        break

            words.extend(chunk_words)

        # Remove overlap:  Sort by time, then filter out any Word entries in
        # the list that are adjacent to another entry corresponding to the same
        # word in the audio.
        words.sort(key=lambda word: word.start)
        words.append(transcription.Word(word="__dummy__"))
        words = [words[i] for i in range(len(words)-1) if not words[i].corresponds(words[i+1])]

        return words, duration

class MultiThreadedTranscriber(Transcriber):
    def __init__(self, kaldi_queue, chunk_len=20, overlap_t=2, nthreads=4):
        super().__init__(kaldi_queue, chunk_len, overlap_t)
            
        self.nthreads = nthreads

    def transcribe(self, wavfile, progress_cb=None):
        wav_obj = wave.open(wavfile, 'rb')
        duration = wav_obj.getnframes() / float(wav_obj.getframerate())
        n_chunks = int(math.ceil(duration / float(self.chunk_len - self.overlap_t)))

        chunks = []

        def transcribe_chunk(idx):
            chunk = self.transcribe_chunk(wavfile, idx)
            chunks.append(chunk)
            self.log_progress(len(chunks), n_chunks, chunk.get("words"), progress_cb)

        pool = Pool(min(n_chunks, self.nthreads))
        pool.map(transcribe_chunk, range(n_chunks))
        pool.close()
        
        return self.combine_chunks(chunks, duration)


if __name__=='__main__':
    # full transcription
    import json
    import sys
    import argparse
    import logging
    import gentle
    from gentle import standard_kaldi, isolated_kaldi
    from gentle import kaldi_queue

    program = argparse.ArgumentParser("transcriber.py")
    program.add_argument("-d", "--debug", action='store_true', help="Enable debug logging")
    program.add_argument("-t", "--threads", type=int, default=4, help="Configure thread count.")
    program.add_argument("-i", "--isolated", action='store_true', help="Execute Kaldi processes in isolation")
    program.add_argument("-s", "--chunk-size", type=int, default=20, help="Configure chunk size.")
    program.add_argument("input_file", type=str)
    program.add_argument("output_file", type=argparse.FileType('w'))
    args = program.parse_args(sys.argv[1:])

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    k_queue = kaldi_queue.build(
        gentle.Resources(), 
        nthreads=args.threads, 
        kaldi_module=isolated_kaldi if args.isolated else standard_kaldi
    )

    if args.threads > 1:
        trans = MultiThreadedTranscriber(k_queue, nthreads=args.threads, chunk_len=args.chunk_size)
    else:
        trans = Transcriber(k_queue, chunk_len=args.chunk_size)

    with gentle.resampled(args.input_file) as filename:
        words, duration = trans.transcribe(filename)

    args.output_file.write(transcription.Transcription(words=words).to_json())

