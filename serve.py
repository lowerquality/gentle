from twisted.web.static import File
from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from twisted.internet import reactor, threads
from twisted.web._responses import FOUND

import json
import logging
import multiprocessing
import os
import shutil
import uuid
import wave

from gentle.util.paths import get_resource, get_datadir
from gentle.util.cyst import Insist

import gentle

class TranscriptionStatus(Resource):
    def __init__(self, status_dict):
        self.status_dict = status_dict
        Resource.__init__(self)

    def render_GET(self, req):
        req.setHeader(b"Content-Type", "application/json")
        return json.dumps(self.status_dict).encode()

class Transcriber():
    def __init__(self, data_dir, nthreads=4, ntranscriptionthreads=2):
        self.data_dir = data_dir
        self.nthreads = nthreads
        self.ntranscriptionthreads = ntranscriptionthreads
        self.resources = gentle.Resources()

        self.full_transcriber = gentle.FullTranscriber(self.resources, nthreads=ntranscriptionthreads)
        self._status_dicts = {}

    def get_status(self, uid):
        return self._status_dicts.setdefault(uid, {})

    def out_dir(self, uid):
        return os.path.join(self.data_dir, 'transcriptions', uid)

    # TODO(maxhawkins): refactor so this is returned by transcribe()
    def next_id(self):
        uid = None
        while uid is None or os.path.exists(os.path.join(self.data_dir, uid)):
            uid = uuid.uuid4().hex[:8]
        return uid

    def transcribe(self, uid, transcript, audio, async_mode, **kwargs):

        status = self.get_status(uid)

        status['status'] = 'STARTED'
        output = {
            'transcript': transcript
        }

        outdir = os.path.join(self.data_dir, 'transcriptions', uid)

        tran_path = os.path.join(outdir, 'transcript.txt')
        with open(tran_path, 'w') as tranfile:
            tranfile.write(transcript)
        audio_path = os.path.join(outdir, 'upload')
        with open(audio_path, 'wb') as wavfile:
            wavfile.write(audio)

        status['status'] = 'ENCODING'

        wavfile = os.path.join(outdir, 'a.wav')
        if gentle.resample(os.path.join(outdir, 'upload'), wavfile) != 0:
            status['status'] = 'ERROR'
            status['error'] = "Encoding failed. Make sure that you've uploaded a valid media file."
            # Save the status so that errors are recovered on restart of the server
            # XXX: This won't work, because the endpoint will override this file
            with open(os.path.join(outdir, 'status.json'), 'w') as jsfile:
                json.dump(status, jsfile, indent=2)
            return

        #XXX: Maybe we should pass this wave object instead of the
        # file path to align_progress
        wav_obj = wave.open(wavfile, 'rb')
        status['duration'] = wav_obj.getnframes() / float(wav_obj.getframerate())
        status['status'] = 'TRANSCRIBING'

        def on_progress(p):
            print(p)
            for k,v in p.items():
                status[k] = v

        if len(transcript.strip()) > 0:
            trans = gentle.ForcedAligner(self.resources, transcript, nthreads=self.nthreads, **kwargs)
        elif self.full_transcriber.available:
            trans = self.full_transcriber
        else:
            status['status'] = 'ERROR'
            status['error']  = 'No transcript provided and no language model for full transcription'
            return

        output = trans.transcribe(wavfile, progress_cb=on_progress, logging=logging)

        # ...remove the original upload
        os.unlink(os.path.join(outdir, 'upload'))

        # Save
        with open(os.path.join(outdir, 'align.json'), 'w') as jsfile:
            jsfile.write(output.to_json(indent=2))
        with open(os.path.join(outdir, 'align.csv'), 'w') as csvfile:
            csvfile.write(output.to_csv())

        # Inline the alignment into the index.html file.
        htmltxt = open(get_resource('www/view_alignment.html')).read()
        htmltxt = htmltxt.replace("var INLINE_JSON;", "var INLINE_JSON=%s;" % (output.to_json()));
        open(os.path.join(outdir, 'index.html'), 'w').write(htmltxt)

        status['status'] = 'OK'

        logging.info('done with transcription.')

        return output

class TranscriptionsController(Resource):
    def __init__(self, transcriber):
        Resource.__init__(self)
        self.transcriber = transcriber

    def getChild(self, uid, req):
        uid = uid.decode()
        out_dir = self.transcriber.out_dir(uid)
        trans_ctrl = File(out_dir)

        # Add a Status endpoint to the file
        trans_status = TranscriptionStatus(self.transcriber.get_status(uid))
        trans_ctrl.putChild(b"status.json", trans_status)

        return trans_ctrl

    def render_POST(self, req):
        uid = self.transcriber.next_id()

        tran = req.args.get(b'transcript', [b''])[0].decode()
        audio = req.args[b'audio'][0]

        disfluency = True if b'disfluency' in req.args else False
        conservative = True if b'conservative' in req.args else False
        kwargs = {'disfluency': disfluency,
                  'conservative': conservative,
                  'disfluencies': set(['uh', 'um'])}

        async_mode = True
        if b'async' in req.args and req.args[b'async'][0] == b'false':
            async_mode = False

        # We need to make the transcription directory here, so that
        # when we redirect the user we are sure that there's a place
        # for them to go.
        outdir = os.path.join(self.transcriber.data_dir, 'transcriptions', uid)
        os.makedirs(outdir)

        # Copy over the HTML
        shutil.copy(get_resource('www/view_alignment.html'), os.path.join(outdir, 'index.html'))

        result_promise = threads.deferToThreadPool(
            reactor, reactor.getThreadPool(),
            self.transcriber.transcribe,
            uid, tran, audio, async_mode, **kwargs)

        if not async_mode:
            def write_result(result):
                '''Write JSON to client on completion'''
                req.setHeader("Content-Type", "application/json")
                req.write(result.to_json(indent=2).encode())
                req.finish()
            result_promise.addCallback(write_result)
            result_promise.addErrback(lambda _: None) # ignore errors

            req.notifyFinish().addErrback(lambda _: result_promise.cancel())

            return NOT_DONE_YET

        req.setResponseCode(FOUND)
        req.setHeader(b"Location", "/transcriptions/%s" % (uid))
        return b''

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
        uid = path.decode().split('.')[0]
        t_dir = self.transcriber.out_dir(uid)
        if os.path.exists(t_dir):
            # TODO: Check that "status" is complete and only create a LazyZipper if so
            # Otherwise, we could have incomplete transcriptions that get permanently zipped.
            # For now, a solution will be hiding the button in the client until it's done.
            lz = LazyZipper(self.cachedir, self.transcriber, uid)
            if not isinstance(path, bytes):
                path = path.encode()
            self.putChild(path, lz)
            return lz
        else:
            return Resource.getChild(self, path, req)

def serve(port=8765, interface='0.0.0.0', installSignalHandlers=0, nthreads=4, ntranscriptionthreads=2, data_dir=get_datadir('webdata')):
    logging.info("SERVE %d, %s, %d", port, interface, installSignalHandlers)

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    zip_dir = os.path.join(data_dir, 'zip')
    if not os.path.exists(zip_dir):
        os.makedirs(zip_dir)

    f = File(data_dir)

    f.putChild(b'', File(get_resource('www/index.html')))
    f.putChild(b'status.html', File(get_resource('www/status.html')))
    f.putChild(b'preloader.gif', File(get_resource('www/preloader.gif')))

    trans = Transcriber(data_dir, nthreads=nthreads, ntranscriptionthreads=ntranscriptionthreads)
    trans_ctrl = TranscriptionsController(trans)
    f.putChild(b'transcriptions', trans_ctrl)

    trans_zippr = TranscriptionZipper(zip_dir, trans)
    f.putChild(b'zip', trans_zippr)

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
    parser.add_argument('--nthreads', default=multiprocessing.cpu_count(), type=int,
                        help='number of alignment threads')
    parser.add_argument('--ntranscriptionthreads', default=2, type=int,
                        help='number of full-transcription threads (memory intensive)')
    parser.add_argument('--log', default="INFO",
                        help='the log level (DEBUG, INFO, WARNING, ERROR, or CRITICAL)')

    args = parser.parse_args()

    log_level = args.log.upper()
    logging.getLogger().setLevel(log_level)

    logging.info('gentle %s' % (gentle.__version__))
    logging.info('listening at %s:%d\n' % (args.host, args.port))

    serve(args.port, args.host, nthreads=args.nthreads, ntranscriptionthreads=args.ntranscriptionthreads, installSignalHandlers=1)
