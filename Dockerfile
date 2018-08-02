FROM ubuntu:latest as builder-kaldi

ENV CPU_CORE 4
ENV DEBIAN_FRONTEND=noninteractive
ENV CXX=clang++

RUN apt-get update && \
	apt-get install -y \
		autoconf \
		automake \
		bzip2 \
		clang \
		ffmpeg \
		g++ \
		gfortran \
		git \
		libatlas3-base \
		libtool \
		make \
		python \
		python3 \
		sox \
		subversion \
		unzip \
		wget \
		zlib1g-dev

WORKDIR /usr/local
# Use the newest kaldi version
RUN git clone https://github.com/kaldi-asr/kaldi.git

# Build Kaldi
WORKDIR /usr/local/kaldi/tools
RUN extras/check_dependencies.sh
RUN make CXX=${CXX} -j $CPU_CORE
RUN extras/install_openblas.sh

WORKDIR /usr/local/kaldi/src
RUN ./configure --static --static-math=yes --static-fst=yes --use-cuda=no --openblas-root=../tools/OpenBLAS/install && \
	make depend -j $CPU_CORE && \
	make -j $CPU_CORE


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

