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

# The `ffmpeg.to_wav` function doesn't set headers properly for web
# browser playback.
def to_wav(infile, outfile):
    return subprocess.call([get_binary('ffmpeg'),
                     '-loglevel', 'panic',
                     '-i', infile,
                     '-ac', '1', '-ar', '8000',
                     '-acodec', 'pcm_s16le',
                     outfile])

class Status():
    def __init__(self, status='Started', text=''):
        self.status = status
        self.text = text

class StatusController(Resource):
    def __init__(self, uid, status_store):
        Resource.__init__(self)
        self.uid = uid
        self.status_store = status_store
    def render_GET(self, req):
        status = self.status_store.get(self.uid, Status())
        return json.dumps({
            "status": status.status,
            "text": status.text
        })

class Transcriber():
    def __init__(self, data_dir, status_store):
        self.data_dir = data_dir
        self.status_store = status_store

    def out_dir(self, uid):
        return os.path.join(self.data_dir, 'transcriptions', uid)

    # TODO(maxhawkins): refactor so this is returned by transcribe()
    def next_id(self):
        uid = None
        while uid is None or os.path.exists(os.path.join(self.data_dir, uid)):
            uid = uuid.uuid4().get_hex()[:8]
        return uid

    def transcribe(self, uid, tran, audio):
        outdir = os.path.join(self.data_dir, 'transcriptions', uid)
        os.makedirs(outdir)

        tran_path = os.path.join(outdir, 'transcript.txt')
        with open(tran_path, 'w') as f:
            f.write(tran)
        audio_path = os.path.join(outdir, 'upload')
        with open(audio_path, 'w') as f:
            f.write(audio)

        wavfile = os.path.join(outdir, 'a.wav')
        self.status_store[uid] = Status("Encoding", "")
        
        if to_wav(os.path.join(outdir, 'upload'), wavfile) != 0:
            self.status_store[uid] = Status("Error", "Encoding failed. Make sure that you've uploaded a valid media file.")
            return 

        with open(os.path.join(outdir, 'transcript.txt')) as f:
            transcript = f.read()

        self.status_store[uid] = Status("Starting transcription", "")

        def onpartial(res):
            logging.info("partial results for %s, %s", uid, str(res))

            self.status_store[uid] = Status("Transcribing", json.dumps(res))

        # Run transcription
        ret = lm_transcribe(wavfile,
            transcript,
            # XXX: should be configurable
            get_resource('PROTO_LANGDIR'),
            get_resource('data/nnet_a_gpu_online'),
            partial_cb=onpartial)

        # Save output to JSON and CSV
        with open(os.path.join(outdir, 'align.json'), 'w') as f:
            json.dump(ret, f, indent=2)
        with open(os.path.join(outdir, 'align.csv', 'w') as f:
            write_csv(ret, f)

        # Finally, copy over the HTML
        shutil.copy(get_resource('www/view_alignment.html'), os.path.join(outdir, 'index.html'))

        # ...and remove the original upload
        os.unlink(os.path.join(outdir, 'upload'))

        self.status_store[uid] = Status("Done", "")

        logging.info('done with transcription.')

        return ret

class TranscriptionsController(Resource):
    def __init__(self, status_store, transcriber):
        Resource.__init__(self)
        self.status_store = status_store
        self.transcriber = transcriber
    
    def getChild(self, uid, req):
        out_dir = self.transcriber.out_dir(uid)
        trans_ctrl = File(out_dir)

        stats_ctrl = StatusController(uid, self.status_store)
        trans_ctrl.putChild('status', stats_ctrl)
        return trans_ctrl

    def render_POST(self, req):
        uid = self.transcriber.next_id()

        tran = req.args['transcript'][0]
        audio = req.args['audio'][0]
        if 'async' in req.args and req.args['async'][0] == 'false':
            result = self.transcriber.transcribe(uid, tran, audio)
            return json.dumps(result)

        reactor.callInThread(self.transcriber.transcribe, uid, tran, audio)

        req.redirect("/status.html#%s" % (uid))
        req.finish()

        return NOT_DONE_YET

def serve(port=8765, interface='0.0.0.0', installSignalHandlers=0, data_dir=get_datadir('webdata')):
    logging.info("SERVE %d, %s, %d", port, interface, installSignalHandlers)
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    f = File(data_dir)

    f.putChild('', File(get_resource('www/index.html')))
    f.putChild('status.html', File(get_resource('www/status.html')))
    
    status_store = {}

    trans = Transcriber(data_dir, status_store)
    trans_ctrl = TranscriptionsController(status_store, trans)
    f.putChild('transcriptions', trans_ctrl)
    
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
