#!/bin/bash

set -e

./install_deps.sh
./install_kaldi.sh
./install_models.sh
cd ext && make
