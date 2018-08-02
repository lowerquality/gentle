FROM ubuntu:latest as builder-kaldi

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
	apt-get install -y clang zlib1g-dev automake autoconf git \
		libtool subversion libatlas3-base ffmpeg python3-pip \
		python3-dev wget unzip sox gfortran python-pip python-dev && \
	apt-get clean

RUN git clone https://github.com/descriptinc/gentle.git gentle
WORKDIR /gentle
RUN git submodule update --init --recursive
WORKDIR /gentle/ext/kaldi/tools
ENV CXX=clang++
RUN make && \
	./extras/install_openblas.sh
WORKDIR /gentle/ext/kaldi/src
RUN ./configure --static --static-math=yes --static-fst=yes --use-cuda=no --openblas-root=../tools/OpenBLAS/install && \
	make depend && \
	make
WORKDIR /gentle/ext
RUN make depend && \
	make

WORKDIR /gentle
RUN ./install_models.sh

FROM python:3-stretch
ADD . /gentle
WORKDIR /gentle/ext
COPY --from=builder-kaldi /gentle/ext/k3 .
COPY --from=builder-kaldi /gentle/ext/m3 .
WORKDIR /gentle/
COPY --from=builder-kaldi /gentle/exp exp

RUN pip3 install .

ENV PORT=8765
EXPOSE 8765

VOLUME /gentle/webdata

CMD python3 serve.py --port $PORT

