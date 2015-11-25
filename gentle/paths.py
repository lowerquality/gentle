import os
import glob
import shutil
import sys

def get_binary(name):
    binpath = name
    if os.path.exists(name):
        binpath = "./%s" % (name)
    return binpath

def get_resource(path):
    # Identity
    return path

def get_datadir(path):
    datadir = path
    if hasattr(sys, "frozen") and sys.frozen == "macosx_app":
        datadir = os.path.join(os.environ['HOME'], '.gentle', path)
    return datadir
