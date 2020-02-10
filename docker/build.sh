cd "$(dirname "$0")"

if [[ -e gentle ]]; then
    rm -rf gentle
fi

mkdir gentle
cp -R ../ext gentle/ext
cp -R ../www gentle/www
cp -R ../gentle gentle/gentle
cp ../align.py gentle/align.py
cp ../setup.py gentle/setup.py
cp ../serve.py gentle/serve.py
cp ../install_models.sh gentle/
cp ../install_language_model.sh gentle/

if [[ -n "$MAKE_NUM_THREADS" ]]; then BUILD_ARGS="$BUILD_ARGS --build-arg MAKE_NUM_THREADS=$MAKE_NUM_THREADS"; fi
if [[ -n "$OPENBLAS_NUM_THREADS" ]]; then BUILD_ARGS="$BUILD_ARGS --build-arg OPENBLAS_NUM_THREADS=$OPENBLAS_NUM_THREADS"; fi
if [[ -n "$OPENBLAS_COMMIT" ]]; then BUILD_ARGS="$BUILD_ARGS --build-arg OPENBLAS_COMMIT=$OPENBLAS_COMMIT"; fi

docker build $BUILD_ARGS -t aif-gentle .

