curl -X POST -F 'audio=@examples/data/lucier.mp3' -F 'transcript=<examples/data/lucier.txt' 'http://localhost:8765/transcriptions?async=false'
