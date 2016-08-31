import argparse
import json
import logging
import multiprocessing
import os
import sys
import tempfile

import gentle
from gentle.forced_aligner import ForcedAligner
from gentle.ffmpeg import to_wav

parser = argparse.ArgumentParser(
        description='Align a transcript to audio by generating a new language model.  Outputs JSON')
parser.add_argument(
        '--nthreads', default=multiprocessing.cpu_count(), type=int,
        help='number of alignment threads')
parser.add_argument(
        '-o', '--output', metavar='output', type=str, 
        help='output filename')
parser.add_argument(
        '--conservative', dest='conservative', action='store_true',
        help='conservative alignment')
parser.set_defaults(conservative=False)
parser.add_argument(
        '--disfluency', dest='disfluency', action='store_true',
        help='include disfluencies (uh, um) in alignment')
parser.set_defaults(disfluency=False)
parser.add_argument(
        '--log', default="INFO",
        help='the log level (DEBUG, INFO, WARNING, ERROR, or CRITICAL)')
parser.add_argument(
        'audiofile', type=str,
        help='audio file')
parser.add_argument(
        'txtfile', type=str,
        help='transcript text file')
args = parser.parse_args()

log_level = args.log.upper()
logging.getLogger().setLevel(log_level)

disfluencies = set(['uh', 'um'])

def on_progress(p):
    for k,v in p.items():
        logging.debug("%s: %s" % (k, v))


with open(args.txtfile) as fh:
    transcript = fh.read()

_, wavfile = tempfile.mkstemp(suffix='.wav')

try:
    resources = gentle.Resources()
    logging.info("converting audio to 8K sampled wav")
    to_wav(args.audiofile, wavfile)
    logging.info("starting alignment")
    aligner = ForcedAligner(resources, transcript, nthreads=args.nthreads, disfluency=args.disfluency, conservative=args.conservative, disfluencies=disfluencies)
    result = aligner.transcribe(wavfile, progress_cb=on_progress, logging=logging)
finally:
    os.unlink(wavfile)

fh = open(args.output, 'w') if args.output else sys.stdout
json.dump(result, fh, indent=2)
if args.output:
    logging.info("output written to %s" % (args.output))
