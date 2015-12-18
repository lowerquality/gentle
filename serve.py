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

from gentle.paths import get_binary, get_resource, get_datadir
from gentle.language_model_transcribe import lm_transcribe_progress
from gentle.transcription import to_csv
import gentle

class EncodingError(Exception):
    '''Raised when ffmpeg failed to encode an audiofile for whatever reason.'''
    pass

# The `ffmpeg.to_wav` function doesn't set headers properly for web
# browser playback.
def to_wav(infile, outfile):
    status = subprocess.call([
        get_binary('ffmpeg'),
        '-loglevel', 'panic',
        '-i', infile,
        '-ac', '1', '-ar', '8000',
        '-acodec', 'pcm_s16le',
        outfile])
    if status != 0:
        raise EncodingError()

class Transcriber():
    def __init__(self, data_dir):
        self.data_dir = data_dir

    def out_dir(self, uid):
        return os.path.join(self.data_dir, 'transcriptions', uid)

    # TODO(maxhawkins): refactor so this is returned by transcribe()
    def next_id(self):
        uid = None
        while uid is None or os.path.exists(os.path.join(self.data_dir, uid)):
            uid = uuid.uuid4().get_hex()[:8]
        return uid

    def save_wav(self, audio_or_id, out_dir):
        '''Transcode and save a wav in the given directory. If
        an id is provided instead of audio bytes, copy the audio
        file from the previous transcription with that id.'''
        out_path = os.path.join(out_dir, 'a.wav')
        upload_path = os.path.join(out_dir, 'upload')

        if len(audio_or_id) == 8: # it's actually an audio id
            src_wavfile = os.path.join(
                self.data_dir,
                'transcriptions',
                audio_or_id,
                'a.wav')
            if not os.path.exists(src_wavfile):
                raise RuntimeError("missing wavfile for '%s'" % (audio_or_id))
            shutil.copy(src_wavfile, out_path)
        else:
            with open(upload_path, 'w') as wavfile:
                wavfile.write(audio_or_id)
            to_wav(upload_path, out_path)
            os.unlink(upload_path)

        return out_path

    def transcribe(self, uid, transcript, audio_or_id):
        output = {
            'status': 'STARTED',
            'transcript': transcript,
        }

        def save():
            with open(os.path.join(outdir, 'align.json'), 'w') as jsfile:
                json.dump(output, jsfile, indent=2)
            with open(os.path.join(outdir, 'align.csv'), 'w') as csvfile:
                csvfile.write(to_csv(output))

        outdir = os.path.join(self.data_dir, 'transcriptions', uid)
        os.makedirs(outdir)

        # Finally, copy over the HTML
        shutil.copy(get_resource('www/view_alignment.html'), os.path.join(outdir, 'index.html'))

        tran_path = os.path.join(outdir, 'transcript.txt')
        with open(tran_path, 'w') as tranfile:
            tranfile.write(transcript)

        output['status'] = 'ENCODING'
        save()

        try:
            wavfile = self.save_wav(audio_or_id, outdir)
        except EncodingError, error:
            logging.info('%r', error)
            output['status'] = 'ERROR'
            output['error'] = "Encoding failed. Make sure that you've uploaded a valid media file."
            save()
            return

        output['status'] = 'TRANSCRIBING'
        save()

        # Run transcription
        progress = lm_transcribe_progress(
            wavfile,
            transcript,
            # XXX: should be configurable
            get_resource('PROTO_LANGDIR'),
            get_resource('data/nnet_a_gpu_online'))
        result = None
        for result in progress:
            output['words'] = result['words']
            output['transcript'] = result['transcript']
            save()

        output['status'] = 'OK'
        save()

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
        return trans_ctrl

    def render_POST(self, req):
        uid = self.transcriber.next_id()

        tran = req.args['transcript'][0]
        audio = req.args['audio'][0]

        async = True
        if 'async' in req.args and req.args['async'][0] == 'false':
            async = False

        result_promise = threads.deferToThreadPool(
            self.reactor, self.reactor.getThreadPool(),
            self.transcriber.transcribe,
            uid, tran, audio)

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

def serve(port=8765, interface='0.0.0.0', installSignalHandlers=0, data_dir=get_datadir('webdata')):
    logging.info("SERVE %d, %s, %d", port, interface, installSignalHandlers)
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    f = File(data_dir)

    f.putChild('', File(get_resource('www/index.html')))
    f.putChild('status.html', File(get_resource('www/status.html')))
    f.putChild('preloader.gif', File(get_resource('www/preloader.gif')))

    trans = Transcriber(data_dir)
    trans_ctrl = TranscriptionsController(trans)
    f.putChild('transcriptions', trans_ctrl)
    
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
