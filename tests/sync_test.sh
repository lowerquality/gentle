curl -X POST -F 'audio=@tests/data/lucier.mp3' -F 'transcript=<tests/data/lucier.txt' 'http://localhost:8765/transcriptions?async=false'
