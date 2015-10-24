#!/bin/bash

# Simplest possible test to ensure there are no regressions when
# refactoring. Run the file and compare its output to a golden
# version. If it's different then something changed.

# TODO(maxhawkins): calculate word error rate instead and set an
# acceptable performance baseline

DIR="$(dirname "${BASH_SOURCE[0]}")"
cd "$DIR/.."

echo "Running test..."

TMPDIR=$(mktemp -dt "gentle_test")

ERR=$(python gentle/language_model_transcribe.py tests/data/lucier.mp3 tests/data/lucier.txt $TMPDIR/got.json 2>&1)
if [ $? -ne 0 ]; then
	echo "lucier.mp3: error running gentle.py"
	echo "$ERR"
	echo "FAIL"
	exit 1
fi

DIFF="$(diff tests/data/lucier_golden.json $TMPDIR/got.json)"

if [ "$DIFF" != "" ]; then
	echo "lucier.mp3: transcript doesn't match golden master"
	echo "$DIFF"
	echo "FAIL"
	exit 1
else
	echo "OK"
fi
