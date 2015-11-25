FROM ubuntu:15.04

RUN DEBIAN_FRONTEND=noninteractive && \
	apt-get update && \
	apt-get install -y zlib1g-dev automake autoconf git \
		libtool subversion libatlas3-base ffmpeg python-pip \
		python-dev wget unzip && \
	apt-get clean
ADD . /gentle
RUN MAKEFLAGS=' -j8' cd /gentle && \
	./install_kaldi.sh && \
	make
RUN cd /gentle && ./install_models.sh

EXPOSE 8765

CMD cd /gentle && python serve.py
