import os
import glob
import logging
import shutil
import sys

def get_binary(name):
    binpath = name
    if hasattr(sys, "frozen"):
        # HACK
        if name == 'ffmpeg':
            name = 'ext/ffmpeg'
        binpath = os.path.abspath(os.path.join(sys._MEIPASS, '..', 'Resources', name))
    elif os.path.exists(name):
        binpath = "./%s" % (name)

    logging.info("binpath %s", binpath)
    return binpath

def get_resource(path):
    rpath = path
    if hasattr(sys, "frozen"):
        rpath = os.path.abspath(os.path.join(sys._MEIPASS, '..', 'Resources', path))
    logging.info("resourcepath %s", rpath)
    return rpath

def get_datadir(path):
    datadir = path
    if hasattr(sys, "frozen"):# and sys.frozen == "macosx_app":
        datadir = os.path.join(os.environ['HOME'], '.gentle', path)
    logging.info("datadir %s", datadir)
    return datadir
