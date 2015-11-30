from twisted.web.static import File
from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from twisted.internet import reactor

import json
import logging
import os
import shutil
import subprocess
import sys
import uuid

from gentle.paths import get_binary, get_resource, get_datadir
from gentle.language_model_transcribe import lm_transcribe, write_csv
import gentle

DATADIR = get_datadir('webdata')

def _next_id():
    uid = None
    while uid is None or os.path.exists(os.path.join(DATADIR, uid)):
        uid = uuid.uuid4().get_hex()[:8]
    return uid

# The `ffmpeg.to_wav` function doesn't set headers properly for web
# browser playback.
def to_wav(infile, outfile):
    return subprocess.call([get_binary('ffmpeg'),
                     '-loglevel', 'panic',
                     '-i', infile,
                     '-ac', '1', '-ar', '8000',
                     '-acodec', 'pcm_s16le',
                     outfile])

class Status(Resource):
    def __init__(self):
        Resource.__init__(self)
        self.uploads = {}
        
    def new_upload(self, uid):
        self.uploads[uid] = TranscriptionStatus()
        self.putChild(uid, self.uploads[uid])

    def set_status(self, uid, status, text):
        self.uploads[uid].cur_status = status
        self.uploads[uid].status_text = text

class TranscriptionStatus(Resource):
    def __init__(self):
        Resource.__init__(self)
        self.cur_status = "Started"
        self.status_text = ""

    def render_GET(self, req):
        return json.dumps({
            "status": self.cur_status,
            "text": self.status_text})

class Uploader(Resource):
    def __init__(self, status):
        Resource.__init__(self)
        self.status = status
    
    def render_POST(self, req):
        uid = _next_id()

        self.status.new_upload(uid)
        
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

    def onpartial(self, res, uid):
        logging.info("partial results for %s, %s", uid, str(res))

        self.status.set_status(uid, "Transcribing", json.dumps(res))

    def transcribe(self, uid, req=None):
        outdir = os.path.join(DATADIR, uid)

        wavfile = os.path.join(outdir, 'a.wav')
        self.status.set_status(uid, "Encoding", "")
        
        if to_wav(os.path.join(outdir, 'upload'), wavfile) != 0:
            self.status.set_status(uid, "Error", "Encoding failed. Make sure that you've uploaded a valid media file.")
            return

        transcript = open(os.path.join(outdir, 'transcript.txt')).read()

        self.status.set_status(uid, "Starting transcription", "")
        # Run transcription
        ret = lm_transcribe(wavfile,
                            transcript,
                            # XXX: should be configurable
                            get_resource('PROTO_LANGDIR'),
                            get_resource('data/nnet_a_gpu_online'),
                            partial_cb=self.onpartial,
                            partial_kwargs={"uid": uid})

        # Save output to JSON and CSV
        json.dump(ret,
                  open(os.path.join(outdir, 'align.json'), 'w'), indent=2)
        write_csv(ret, open(os.path.join(outdir, 'align.csv'), 'w'))

        # Finally, copy over the HTML
        shutil.copy(get_resource('www/view_alignment.html'), os.path.join(outdir, 'index.html'))

        # ...and remove the original upload
        os.unlink(os.path.join(outdir, 'upload'))

        self.status.set_status(uid, "Done", "")        

        logging.info('done with transcription.')

def serve(port=8765, interface='0.0.0.0', installSignalHandlers=0):
    logging.info("SERVE %d, %s, %d", port, interface, installSignalHandlers)
    
    if not os.path.exists(DATADIR):
        os.makedirs(DATADIR)
    
    f = File(DATADIR)

    f.putChild('', File(get_resource('www/index.html')))
    f.putChild('status.html', File(get_resource('www/status.html')))

    stats = Status()
    f.putChild("status", stats)
    
    up = Uploader(stats)

    f.putChild('transcribe', up)
    
    s = Site(f)
    logging.info("about to listen")
    reactor.listenTCP(port, s, interface=interface)
    logging.info("listening")

    reactor.run(installSignalHandlers=installSignalHandlers)
    
    
if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Align a transcript to audio by generating a new language model.')
    parser.add_argument('--host', default="0.0.0.0",
                       help='host to run http server on')
    parser.add_argument('--port', default=8765, type=int,
                        help='port number to run http server on')
    parser.add_argument('--log', default="INFO",
                        help='the log level (DEBUG, INFO, WARNING, ERROR, or CRITICAL)')

    args = parser.parse_args()

    log_level = args.log.upper()
    logging.getLogger().setLevel(log_level)

    logging.info('gentle %s' % (gentle.__version__))
    logging.info('listening at %s:%d\n' % (args.host, args.port))

    serve(args.port, args.host, installSignalHandlers=1)
