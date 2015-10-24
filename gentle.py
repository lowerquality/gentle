import os
import sys
import tempfile

from gentle.language_model_transcribe import lm_transcribe

from flask import jsonify, request, Flask, render_template
app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return """<html>
    <head>
        <meta charset="utf-8" />
        <style>
            body { font-family: sans-serif; }
            textarea { width: 500px; height: 20em; }
            input, textarea { margin: 1em 0; }
        </style>
    </head>
    <body>
        <form action="/transcribe" method="POST" enctype="multipart/form-data">
          Audio:<br>
          <input type=file name=audio><br>
          <br>
          Transcript:<br>
          <textarea name="transcript"></textarea><br>
          <input type=submit value=Align>
        </form>
    </body>
    </html>"""

@app.route('/transcribe', methods=['POST'])
def transcribe():
    transcript = request.form['transcript']

    audio = request.files['audio']
    _, extension = os.path.splitext(audio.filename)
    audio_file = tempfile.NamedTemporaryFile(suffix=extension)
    audio.save(audio_file)

    proto_langdir = app.config['proto_langdir']
    nnet_dir = app.config['nnet_dir']

    aligned = lm_transcribe(audio_file.name, transcript,
        proto_langdir, nnet_dir)
    return jsonify(transcript=aligned)


if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Align a transcript to audio by generating a new language model.')
    parser.add_argument('--proto_langdir', default="PROTO_LANGDIR",
                       help='path to the prototype language directory')
    parser.add_argument('--nnet_dir', default="data",
                       help='path to the kaldi neural net model directory')
    parser.add_argument('--port', default=8080, type=int,
                        help='port number to run http server on')

    args = parser.parse_args()

    app.config['proto_langdir'] = args.proto_langdir
    app.config['nnet_dir'] = args.nnet_dir
    
    app.run(port=args.port)
    
