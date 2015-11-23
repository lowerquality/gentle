#!/bin/bash

set -e

./install_deps.sh
./install_kaldi.sh
make
./install_models.sh
