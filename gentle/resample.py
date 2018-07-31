import os
import subprocess
import tempfile

from contextlib import contextmanager


from .util.paths import get_binary

FFMPEG = get_binary("ffmpeg")

def resample(infile, outfile, offset=None, duration=None):
    if not os.path.isfile(infile):
        raise IOError("Not a file: %s" % infile)

    '''
    Use FFMPEG to convert a media file to a wav file sampled at 8K
    '''
    if offset is None:
        offset = []
    else:
        offset = ['-ss', str(offset)]
    if duration is None:
        duration = []
    else:
        duration = ['-t', str(duration)]

    cmd = [
        FFMPEG,
        '-loglevel', 'panic',
        '-y',
    ] + offset + [
        '-i', infile,
    ] + duration + [
        '-ac', '1', '-ar', '8000',
        '-acodec', 'pcm_s16le',
        outfile
    ]
    return subprocess.call(cmd)

@contextmanager
def resampled(infile, offset=None, duration=None):
    with tempfile.NamedTemporaryFile(suffix='.wav') as fp:
        if resample(infile, fp.name, offset, duration) != 0:
            raise RuntimeError("Unable to resample/encode '%s'" % infile)
        yield fp.name
