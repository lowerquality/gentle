import subprocess

from paths import get_binary

FFMPEG = get_binary("ffmpeg")

def to_wav(infile, outfile):
    '''
    Use FFMPEG to convert a media file to a wav file
    '''
    return subprocess.call([FFMPEG,
                            '-loglevel', 'panic',
                            '-y',
                            '-i', infile,
                            '-ac', '1', '-ar', '8000',
                            '-acodec', 'pcm_s16le',
                            outfile])
