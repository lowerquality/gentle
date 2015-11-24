import os
import glob
import shutil
import sys

if hasattr(sys, "frozen") and sys.frozen == "macosx_app":
    print 'FROZEN!'
else:
    print 'NOT FROZEN!'

def get_binary(name):
    binpath = name
    if os.path.exists(name):
        binpath = "./%s" % (name)

    print 'get_binary', name, binpath
    return binpath

def get_resource(path):
    # Identity
    return path

def get_datadir(path):
    datadir = path
    if hasattr(sys, "frozen") and sys.frozen == "macosx_app":
        datadir = os.path.join(os.environ['HOME'], '.gentle', path)

    print 'get_datadir', path, datadir
    return datadir
