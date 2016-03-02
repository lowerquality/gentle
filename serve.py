from twisted.web.static import File
from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from twisted.internet import reactor as default_reactor
from twisted.web._responses import FOUND
from twisted.internet import threads

import json
import logging
import os
import shutil
import subprocess
import sys
import uuid
import wave

from gentle.paths import get_binary, get_resource, get_datadir
from gentle.language_model_transcribe import align_progress
from gentle.transcription import to_csv
from gentle.cyst import Insist
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

class TranscriptionStatus(Resource):
    def __init__(self, status_dict):
        self.status_dict = status_dict
        Resource.__init__(self)
        
    def render_GET(self, req):
        req.headers["Content-Type"] = "application/json"
        return json.dumps(self.status_dict)

class Transcriber():
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self._status_dicts = {}

    def get_status(self, uid):
        return self._status_dicts.setdefault(uid, {})

    def out_dir(self, uid):
        return os.path.join(self.data_dir, 'transcriptions', uid)

    # TODO(maxhawkins): refactor so this is returned by transcribe()
    def next_id(self):
        uid = None
        while uid is None or os.path.exists(os.path.join(self.data_dir, uid)):
            uid = uuid.uuid4().get_hex()[:8]
        return uid

    def transcribe(self, uid, transcript, audio, async):
        status = self.get_status(uid)

        status['status'] = 'STARTED'
        output = {
            'transcript': transcript
        }

        def save():
            with open(os.path.join(outdir, 'align.json'), 'w') as jsfile:
                json.dump(output, jsfile, indent=2)
            with open(os.path.join(outdir, 'align.csv'), 'w') as csvfile:
                csvfile.write(to_csv(output))

        outdir = os.path.join(self.data_dir, 'transcriptions', uid)                

        tran_path = os.path.join(outdir, 'transcript.txt')
        with open(tran_path, 'w') as tranfile:
            tranfile.write(transcript)
        audio_path = os.path.join(outdir, 'upload')
        with open(audio_path, 'w') as wavfile:
            wavfile.write(audio)

        status['status'] = 'ENCODING'
        # with open(os.path.join(outdir, 'align.json'), 'w') as alignfile:
            # json.dump(output, alignfile, indent=2)

        wavfile = os.path.join(outdir, 'a.wav')
        if to_wav(os.path.join(outdir, 'upload'), wavfile) != 0:
            status['status'] = 'ERROR'
            status['error'] = "Encoding failed. Make sure that you've uploaded a valid media file."
            # Save the status so that errors are recovered on restart of the server
            # XXX: This won't work, because the endpoint will override this file
            with open(os.path.join(outdir, 'status.json'), 'w') as jsfile:
                json.dump(status, jsfile, indent=2)
            return

        # Find the duration

        #XXX: Maybe we should pass this wave object instead of the
        # file path to align_progress
        wav_obj = wave.open(wavfile, 'r')
        status['duration'] = wav_obj.getnframes() / float(wav_obj.getframerate())

        status['status'] = 'TRANSCRIBING'

        # Run transcription
        progress = align_progress(
            wavfile,
            transcript,
            # XXX: should be configurable
            get_resource('PROTO_LANGDIR'),
            get_resource('data/nnet_a_gpu_online'),
            want_progress=True)
        result = None
        for result in progress:
            if result.get("error") is not None:
                status["status"] = "ERROR"
                status["error"] = result["error"]
                
                # Save the status so that errors are recovered on restart of the server
                # XXX: This won't work, because the endpoint will override this file
                # XXX(2): duplicated code.
                with open(os.path.join(outdir, 'status.json'), 'w') as jsfile:
                    json.dump(status, jsfile, indent=2)
                return
                
            elif result.get("preview") is not None:
                status["message"] = result["preview"]
                status["t"] = result["t"]
            else:
                output['words'] = result['words']
                output['transcript'] = result['transcript']
            #save()

        # ...and remove the original upload
        os.unlink(os.path.join(outdir, 'upload'))

        save()

        # Inline the alignment into the index.html file.
        htmltxt = open(get_resource('www/view_alignment.html')).read()
        htmltxt = htmltxt.replace("var INLINE_JSON;", "var INLINE_JSON=%s;" % (json.dumps(output)));
        open(os.path.join(outdir, 'index.html'), 'w').write(htmltxt)

        status['status'] = 'OK'

        logging.info('done with transcription.')

        return result

class TranscriptionsController(Resource):
    def __init__(self, transcriber, reactor=default_reactor):
        Resource.__init__(self)
        self.transcriber = transcriber
        self.reactor = reactor
    
    def getChild(self, uid, req):
        out_dir = self.transcriber.out_dir(uid)
        trans_ctrl = File(out_dir)

        # Add a Status endpoint to the file
        trans_status = TranscriptionStatus(self.transcriber.get_status(uid))
        trans_ctrl.putChild("status.json", trans_status)
        
        return trans_ctrl

    def render_POST(self, req):
        uid = self.transcriber.next_id()

        tran = req.args['transcript'][0]
        audio = req.args['audio'][0]

        async = True
        if 'async' in req.args and req.args['async'][0] == 'false':
            async = False

        # We need to make the transcription directory here, so that
        # when we redirect the user we are sure that there's a place
        # for them to go.
        outdir = os.path.join(self.transcriber.data_dir, 'transcriptions', uid)
        os.makedirs(outdir)

        # Copy over the HTML
        shutil.copy(get_resource('www/view_alignment.html'), os.path.join(outdir, 'index.html'))

        result_promise = threads.deferToThreadPool(
            self.reactor, self.reactor.getThreadPool(),
            self.transcriber.transcribe,
            uid, tran, audio, async)

        if not async:
            def write_result(result):
                '''Write JSON to client on completion'''
                req.headers["Content-Type"] = "application/json"
                req.write(json.dumps(result, indent=2))
                req.finish()
            result_promise.addCallback(write_result)
            result_promise.addErrback(lambda _: None) # ignore errors

            req.notifyFinish().addErrback(lambda _: result_promise.cancel())

            return NOT_DONE_YET

        req.setResponseCode(FOUND)
        req.setHeader(b"Location", "/transcriptions/%s" % (uid))
        return ''

class LazyZipper(Insist):
    def __init__(self, cachedir, transcriber, uid):
        self.transcriber = transcriber
        self.uid = uid
        Insist.__init__(self, os.path.join(cachedir, '%s.zip' % (uid)))

    def serialize_computation(self, outpath):
        shutil.make_archive('.'.join(outpath.split('.')[:-1]), # We need to strip the ".zip" from the end
                            "zip",                             # ...because `shutil.make_archive` adds it back
                            os.path.join(self.transcriber.out_dir(self.uid)))

class TranscriptionZipper(Resource):
    def __init__(self, cachedir, transcriber):
        self.cachedir = cachedir
        self.transcriber = transcriber
        Resource.__init__(self)
    
    def getChild(self, path, req):
        uid = path.split('.')[0]
        t_dir = self.transcriber.out_dir(uid)
        if os.path.exists(t_dir):
            # TODO: Check that "status" is complete and only create a LazyZipper if so
            # Otherwise, we could have incomplete transcriptions that get permanently zipped.
            # For now, a solution will be hiding the button in the client until it's done.
            lz = LazyZipper(self.cachedir, self.transcriber, uid)
            self.putChild(path, lz)
            return lz
        else:
            return Resource.getChild(self, path, req)

def serve(port=8765, interface='0.0.0.0', installSignalHandlers=0, data_dir=get_datadir('webdata')):
    logging.info("SERVE %d, %s, %d", port, interface, installSignalHandlers)
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    zip_dir = os.path.join(data_dir, 'zip')
    if not os.path.exists(zip_dir):
        os.makedirs(zip_dir)
    
    f = File(data_dir)

    f.putChild('', File(get_resource('www/index.html')))
    f.putChild('status.html', File(get_resource('www/status.html')))
    f.putChild('preloader.gif', File(get_resource('www/preloader.gif')))

    trans = Transcriber(data_dir)
    trans_ctrl = TranscriptionsController(trans)
    f.putChild('transcriptions', trans_ctrl)

    trans_zippr = TranscriptionZipper(zip_dir, trans)
    f.putChild('zip', trans_zippr)
    
    s = Site(f)
    logging.info("about to listen")
    default_reactor.listenTCP(port, s, interface=interface)
    logging.info("listening")

    default_reactor.run(installSignalHandlers=installSignalHandlers)
    
    
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
