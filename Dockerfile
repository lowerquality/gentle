FROM ubuntu:16.04 as builder-kaldi

RUN DEBIAN_FRONTEND=noninteractive && \
	apt-get update && \
	apt-get install -y zlib1g-dev automake autoconf git \
		libtool subversion libatlas3-base ffmpeg python-pip \
		python-dev wget unzip sox && \
	apt-get clean

ADD ./ext /gentle/ext
WORKDIR /gentle/ext
RUN MAKEFLAGS=' -j8' ./install_kaldi.sh
RUN make depend && make
WORKDIR /gentle
RUN ./install_models.sh

FROM python:2-stretch 

ADD . /gentle
WORKDIR /gentle/ext
COPY --from=builder-kaldi /gentle/ext .
WORKDIR /gentle/
RUN pip install .

ENV PORT=8765
EXPOSE 8765

VOLUME /gentle/webdata

CMD cd /gentle && python serve.py --port $PORT

