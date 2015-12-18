'''A web service interface to Gentle'''

import json
import logging
import os
import shutil
import subprocess
import uuid

from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from twisted.web.static import File

from gentle.paths import get_binary, get_resource, get_datadir
from gentle.language_model_transcribe import lm_transcribe_progress
from gentle.transcription import to_csv
from gentle import __version__

# The `ffmpeg.to_wav` function doesn't set headers properly for web
# browser playback.
def to_wav(infile, outfile):
    '''Read infile, convert it to an 8kHz wav, and write it to outfile'''
    return subprocess.call([
        get_binary('ffmpeg'),
        '-loglevel', 'panic',
        '-i', infile,
        '-ac', '1', '-ar', '8000',
        '-acodec', 'pcm_s16le',
        outfile])

class Transcriber(object):
    '''Handles running a transcription and saving the results'''

    def __init__(self, data_dir):
        self.data_dir = data_dir

    def out_dir(self, uid):
        '''Return the file system path for the given transcription id'''
        return os.path.join(self.data_dir, 'transcriptions', uid)

    # TODO(maxhawkins): refactor so this is returned by transcribe()
    def next_id(self):
        '''Get a unique ID for use as a trancription id'''
        uid = None
        while uid is None or os.path.exists(os.path.join(self.data_dir, uid)):
            uid = uuid.uuid4().get_hex()[:8]
        return uid

    def transcribe(self, uid, transcript, audio):
        '''Run transcription and save the results periodically.'''
        output = {
            'status': 'STARTED',
            'transcript': transcript,
        }

        def save():
            '''Persist the output object to storage.'''
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
        audio_path = os.path.join(outdir, 'upload')
        with open(audio_path, 'w') as wavfile:
            wavfile.write(audio)

        output['status'] = 'ENCODING'
        with open(os.path.join(outdir, 'align.json'), 'w') as alignfile:
            json.dump(output, alignfile, indent=2)

        wavfile = os.path.join(outdir, 'a.wav')
        if to_wav(os.path.join(outdir, 'upload'), wavfile) != 0:
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

        # ...and remove the original upload
        os.unlink(os.path.join(outdir, 'upload'))

        output['status'] = 'OK'
        save()

        logging.info('done with transcription.')

        return result

class TranscriptionsController(Resource):
    '''JSON interface to the Transcriber model'''

    def __init__(self, transcriber):
        Resource.__init__(self)
        self.transcriber = transcriber

    def getChild(self, uid, _):
        out_dir = self.transcriber.out_dir(uid)
        trans_ctrl = File(out_dir)
        return trans_ctrl

    # pylint: disable=invalid-name
    def render_POST(self, req):
        '''POST /transcriptions

        Parameters:
            transcript: text transcript to be aligned or none if transcribing
            audio: a binary-formatted audio file in any codec ffmpeg supports
            async: if false, blocks and returns the final transcription
        '''
        uid = self.transcriber.next_id()

        tran = req.args['transcript'][0]
        audio = req.args['audio'][0]

        async = True
        if 'async' in req.args and req.args['async'][0] == 'false':
            async = False

        def respond():
            '''Asynchronously transcribe and respond'''
            if async:
                req.redirect("/transcriptions/%s" % (uid))
                req.finish()

            result = self.transcriber.transcribe(uid, tran, audio)

            if not async:
                req.headers["Content-Type"] = "application/json"
                req.write(json.dumps(result, indent=2))
                req.finish()
        reactor.callInThread(respond)

        return NOT_DONE_YET

def build_site(data_dir):
    '''Construct a twisted Site mapping routes to the correct controllers'''
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    root = File(data_dir)

    root.putChild('', File(get_resource('www/index.html')))
    root.putChild('status.html', File(get_resource('www/status.html')))
    root.putChild('preloader.gif', File(get_resource('www/preloader.gif')))

    trans = Transcriber(data_dir)
    trans_ctrl = TranscriptionsController(trans)
    root.putChild('transcriptions', trans_ctrl)

    return Site(root)


def main():
    '''Align a transcript to audio by generating a new language model.'''
    import argparse

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument(
        '--host',
        default="0.0.0.0",
        help='host to run http server on')
    parser.add_argument(
        '--port',
        default=8765,
        type=int,
        help='port number to run http server on')
    parser.add_argument(
        '--log',
        default="INFO",
        help='log level (DEBUG, INFO, WARNING, ERROR, or CRITICAL)')
    parser.add_argument(
        '--data-dir',
        default=get_datadir('webdata'),
        help='directory where transcription results are persisted')

    args = parser.parse_args()

    log_level = args.log.upper()
    logging.getLogger().setLevel(log_level)

    logging.info('gentle %s', __version__)
    logging.info('listening at %s:%d', args.host, args.port)

    site = build_site(args.data_dir)
    reactor.listenTCP(args.port, site, interface=args.host)
    reactor.run(installSignalHandlers=1)

if __name__ == '__main__':
    main()
