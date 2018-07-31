FROM ubuntu:16.04 as builder-kaldi

RUN DEBIAN_FRONTEND=noninteractive && \
	apt-get update && \
	apt-get install -y zlib1g-dev automake autoconf git \
		libtool subversion libatlas3-base ffmpeg python-pip \
		python-dev wget unzip && \
	apt-get clean

ADD ext /gentle/ext
RUN MAKEFLAGS=' -j8' cd /gentle/ext && \
	./install_kaldi.sh && \
	make && rm -rf kaldi *.o

FROM python:2-stretch 
ADD . /gentle
WORKDIR /gentle/ext
COPY --from=builder-kaldi /gentle/ext .
WORKDIR /gentle/
RUN pip install .
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install unzip && apt-get clean
RUN ./install_models.sh

EXPOSE 8765
ENV PORT=8765

VOLUME /gentle/webdata

CMD cd /gentle && python serve.py --port $PORT

