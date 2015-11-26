import subprocess

from paths import get_binary

FFMPEG = get_binary("ffmpeg")

def to_wav(inpath, outpath, R=8000, depth=16, nchannels=1, start=0):
    '''
    Use FFMPEG to convert a media file to a wav file with the given
    sample format.
    '''
    subprocess.check_output([FFMPEG,
      '-ss', "%f" % (start),
      '-i', inpath,
      '-loglevel', 'panic',
      '-ss', "%f" % (start),
      '-vn',
      '-ar', str(R),
      '-ac', str(nchannels),
      '-f', 'wav',
      '-acodec', 'pcm_s16le',
      outpath])
