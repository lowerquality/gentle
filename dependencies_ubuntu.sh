sudo apt-get install -y zlib1g-dev automake autoconf git libtool subversion \
     libatlas3-base ffmpeg python-pip
     
# Kaldi seems to depend on this... 
sudo ln -s -f bash /bin/sh

sudo pip install .
