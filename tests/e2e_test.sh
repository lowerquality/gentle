#!/bin/bash

# Simplest possible test to ensure there are no regressions when
# refactoring. Run the file and compare its output to a golden
# version. If it's different then something changed.

# TODO(maxhawkins): calculate word error rate instead and set an
# acceptable performance baseline

DIR="$(dirname "${BASH_SOURCE[0]}")"
cd "$DIR/.."

echo "Running test..."

WANT="$(cat tests/data/lucier_golden.json | md5)"
GOT="$(python gentle.py tests/data/lucier.mp3 tests/data/lucier.txt - 2>/dev/null | md5)"

if [[ "$WANT" != "$GOT" ]]; then
	echo "transcript for lucier.mp3: MD5 = '$GOT', expected '$WANT'"
	echo "FAIL"
	exit 1
else
	echo "OK"
fi
