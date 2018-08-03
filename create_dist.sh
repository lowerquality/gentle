#!/bin/sh

DIST_FOLDER=gentle_aligner

# Copy the compiled products
mkdir -p ${DIST_FOLDER}/ext
cp ext/k3 ${DIST_FOLDER}/ext/
cp ext/m3 ${DIST_FOLDER}/ext/

cp -r gentle ${DIST_FOLDER}/
cp *.py ${DIST_FOLDER}/
cp COPYING ${DIST_FOLDER}/

tar czf gentle_aligner.tar.gz ${DIST_FOLDER}
