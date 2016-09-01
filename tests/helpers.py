import json
import os
import pytest

_thisdir = os.path.dirname(os.path.realpath(__file__))
_datadir = os.path.join(_thisdir, "data")

def input_path(name):
    return os.path.join(_datadir, "inputs", name)

def result_path(name):
    return os.path.join(_datadir, "results", name)

def result_json(name):
    with open(result_path(name + ".json")) as f:
        return json.loads(f.read())

def input_data(filename):
    with open(input_path(filename)) as fh:
        return fh.read();
