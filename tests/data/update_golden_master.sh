#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

python $DIR/../../gentle/transcribe.py $DIR/lucier.mp3 $DIR/lucier.txt $DIR/lucier_golden.json
