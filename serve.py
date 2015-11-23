from twisted.web.static import File
from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from twisted.internet import reactor

import os
import uuid
import json
import shutil
import subprocess

from gentle.language_model_transcribe import lm_transcribe, write_csv

DATADIR = 'webdata'

def _next_id():
    uid = None
    while uid is None or os.path.exists(os.path.join(DATADIR, uid)):
        uid = uuid.uuid4().get_hex()[:8]
    return uid

# The `ffmpeg.to_wav` function doesn't set headers properly for web
# browser playback.
def to_wav(infile, outfile):
    subprocess.call(['ffmpeg', '-i', infile,
                     '-ac', '1', '-ar', '8000',
                     '-acodec', 'pcm_s16le',
                     outfile])

class Uploader(Resource):
    def render_POST(self, req):
        uid = _next_id()
        outdir = os.path.join(DATADIR, uid)
        os.makedirs(outdir)

        open(os.path.join(outdir, 'transcript.txt'), 'w').write(
            req.args['transcript'][0])

        data = req.args['audio'][0]
        open(os.path.join(outdir, 'upload'), 'w').write(
            data)

        reactor.callInThread(self.transcribe, uid, req=req)

        req.redirect("/status.html#%s" % (uid))
        req.finish()

        return NOT_DONE_YET

    def transcribe(self, uid, req=None):
        outdir = os.path.join(DATADIR, uid)

        wavfile = os.path.join(outdir, 'a.wav')        
        to_wav(os.path.join(outdir, 'upload'), wavfile)

        # Run transcription
        ret = lm_transcribe(wavfile,
                            open(os.path.join(outdir, 'transcript.txt')).read(),
                            # XXX
                            'PROTO_LANGDIR',
                            'data')

        # Save output to JSON and CSV
        json.dump({"words": ret}, open(os.path.join(outdir, 'align.json'), 'w'), indent=2)
        write_csv(ret, open(os.path.join(outdir, 'align.csv'), 'w'))

        # Finally, copy over the HTML
        shutil.copy('www/view_alignment.html', os.path.join(outdir, 'index.html'))

        # ...and remove the original upload
        os.unlink(os.path.join(outdir, 'upload'))

        print 'done with transcription.'
    
if __name__=='__main__':
    if not os.path.exists(DATADIR):
        os.makedirs(DATADIR)
    
    f = File(DATADIR)

    f.putChild('', File('www/index.html'))
    f.putChild('status.html', File('www/status.html'))
    
    up = Uploader()

    f.putChild('transcribe', up)
    
    s = Site(f)
    reactor.listenTCP(8765, s, interface='0.0.0.0')
    reactor.run()
