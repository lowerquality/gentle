from gentle.paths import get_binary
import subprocess

FFMPEG = get_binary("ffmpeg")

def to_wav(path, R=8000, depth=16, nchannels=1, start=0):
    '''
    Use FFMPEG to convert a media file to a wav file with the given
    sample format.

    Returns an IO object so the results can be streamed.
    '''
    cmd = [FFMPEG,
           '-ss', "%f" % (start),
           '-i', path,
           '-ss', "%f" % (start),
           '-vn',
           '-ar', str(R),
           '-ac', str(nchannels),
           '-f', 'wav',
           '-acodec', 'pcm_s16le',
           '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=open('/dev/null', 'w'))
    
    return p.stdout
