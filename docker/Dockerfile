FROM python:3.7 as builder

ARG MAKE_NUM_THREADS=4
ARG OPENBLAS_NUM_THREADS=$MAKE_NUM_THREADS
ENV MAKEFLAGS=" -j$MAKE_NUM_THREADS"

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    zlib1g-dev \
    automake \
    autoconf \
    unzip \
    git \
    gfortran \
    libtool \
    subversion \
    g++

ADD gentle/ext /gentle/ext
WORKDIR /gentle/ext

# Compile Kaldi using OpenBLAS
ARG OPENBLAS_COMMIT=tags/v0.3.7
RUN cd kaldi/tools && make 
RUN cd kaldi/tools && test -e OpenBLAS || git clone https://github.com/xianyi/OpenBLAS.git
RUN cd kaldi/tools/OpenBLAS && git checkout $OPENBLAS_COMMIT && cd .. && \
    ./extras/install_openblas.sh
RUN cd kaldi/src && \
    ./configure --static --static-math=yes --static-fst=yes --use-cuda=no --openblas-root=../tools/OpenBLAS/install && \
    make depend

# Build k3 and m3 binaries
RUN make depend && make && rm -rf kaldi *.o

# Download models
WORKDIR /gentle
ADD gentle/install_language_model.sh ./
ADD gentle/install_models.sh ./
RUN ./install_models.sh && ./install_language_model.sh

FROM python:3.7

# Required dependencies to run k3 and audio file transcription
RUN apt-get update && apt-get install sox ffmpeg gfortran

COPY --from=builder /gentle/ext/k3 /gentle/ext/k3
COPY --from=builder /gentle/ext/m3 /gentle/ext/m3
COPY --from=builder /gentle/exp /gentle/exp
ADD gentle/gentle /gentle/gentle
ADD gentle/*.py /gentle/
ADD genlte/www /gentle/www

WORKDIR /gentle
RUN python3 setup.py develop && rm setup.py
ENV PYTHONPATH="$PYTHONPATH:/gentle"

EXPOSE 8765
VOLUME /gentle/webdata
CMD python3 serve.py

