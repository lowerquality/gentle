FROM ubuntu:16.04 as builder-kaldi

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

ENV KALDI_BASE=/usr/local/kaldi/src/
WORKDIR /usr/local/gentle

RUN apt-get install -y gdb cgdb python3-pip curl

ADD ./install_models.sh .
RUN ./install_models.sh
ADD ./gentle/ ./gentle/
ADD ./www ./www/
ADD ./ext ./ext/
ADD ./*.py ./

WORKDIR /usr/local/gentle/ext
RUN make depend KALDI_BASE=$KALDI_BASE -j $CPU_CORE
RUN make KALDI_BASE=$KALDI_BASE -j $CPU_CORE

FROM ubuntu:16.04 as gentle-packer
WORKDIR /gentle
COPY --from=builder-kaldi /usr/local/gentle/ext/m3 ./ext/
COPY --from=builder-kaldi /usr/local/gentle/ext/k3 ./ext/
ADD . .
RUN ./create_dist.sh
RUN mkdir ./output
RUN cp ./gentle_aligner.tar.gz ./output/
VOLUME /gentle/output

FROM ubuntu:16.04 as gentle
RUN apt-get update
RUN	apt-get install -y \
		libgfortran3 \
		libatlas3-base \
		ffmpeg \
		python3 \
		python3-pip

COPY --from=gentle-packer /gentle/gentle_aligner.tar.gz .
RUN tar xzvf gentle_aligner.tar.gz
WORKDIR /gentle_aligner

COPY --from=builder-kaldi /usr/local/gentle/exp/ ./exp/

RUN pip3 install .
ENV PORT=8765
EXPOSE 8765

VOLUME /gentle_aligner/webdata

CMD python3 serve.py --port $PORT
