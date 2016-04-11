import gentle.standard_kaldi as standard_kaldi
import numm3
from Queue import Queue
from multiprocessing.pool import ThreadPool as Pool
import json
import math
import sys

AUDIOPATH = sys.argv[1]
JSON_OUT  = sys.argv[2]

N_THREADS = 4
T_PER_CHUNK = 10
OVERLAP_T = 2

kaldi_queue = Queue()
for i in range(N_THREADS):
    kaldi_queue.put(standard_kaldi.Kaldi())

# Preload entire audio
audiobuf  = numm3.sound2np(AUDIOPATH, R=8000, nchannels=1)
n_chunks = int(math.ceil(len(audiobuf) / (8000.0 * (T_PER_CHUNK-OVERLAP_T))))

print 'sharding into %d chunks' % (n_chunks)

chunks = []                   # (idx, [words])

def transcribe_chunk(idx):
    st = idx * (T_PER_CHUNK-OVERLAP_T) * 8000
    end= st + T_PER_CHUNK * 8000

    buf = audiobuf[st:end]
    print buf.shape

    k = kaldi_queue.get()

    # # Break into 2s chunks
    # n_buf_chunks = int(buf.shape[0] / 16000.0

    k.push_chunk(buf.tostring())
    
    ret = k.get_final()
    print ' '.join([X['word'] for X in ret])
    k.reset()

    chunks.append({"start": idx*(T_PER_CHUNK-OVERLAP_T), "words": ret})

    print '%d chunks (of %d)' % (len(chunks), n_chunks)

    kaldi_queue.put(k)

    
pool = Pool(N_THREADS)
pool.map(transcribe_chunk, range(n_chunks))
pool.close()
pool.join()

chunks.sort(key=lambda x: x['start'])

json.dump(chunks, open(JSON_OUT, 'w'), indent=2)
