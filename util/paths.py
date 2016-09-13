import os
import glob
import logging
import shutil
import sys

def get_binary(name):
    binpath = name
    if hasattr(sys, "frozen"):
        binpath = os.path.abspath(os.path.join(sys._MEIPASS, '..', 'Resources', name))
    elif os.path.exists(name):
        binpath = "./%s" % (name)

    logging.debug("binpath %s", binpath)
    return binpath

def get_resource(path):
    rpath = path
    if hasattr(sys, "frozen"):
        rpath = os.path.abspath(os.path.join(sys._MEIPASS, '..', 'Resources', path))
        if not os.path.exists(rpath):
            # DMG may be read-only; fall-back to datadir (ie. so language models can be added)
            rpath = get_datadir(path)
    logging.debug("resourcepath %s", rpath)
    return rpath

def get_datadir(path):
    datadir = path
    if hasattr(sys, "frozen"):# and sys.frozen == "macosx_app":
        datadir = os.path.join(os.environ['HOME'], '.gentle', path)
    logging.debug("datadir %s", datadir)
    return datadir
