FROM ubuntu:15.04

ADD . /gentle
RUN DEBIAN_FRONTEND=noninteractive cd /gentle && ./install_deps.sh && apt-get clean
RUN cd /gentle && ./install_kaldi.sh && make
RUN cd /gentle && ./install_models.sh
RUN cd /gentle && make

EXPOSE 8765

CMD cd /gentle && python serve.py
