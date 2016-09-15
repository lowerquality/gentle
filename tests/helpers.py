import json
import os
import pytest

_this_dir = os.path.dirname(os.path.realpath(__file__))
_data_dir = os.path.join(_this_dir, "data")
_input_dir = os.path.join(_data_dir, "input")
_expected_dir = os.path.join(_data_dir, "expected")
_result_dir = os.path.join(_data_dir, "tmp")

def input_path(name):
    return os.path.join(_input_dir, name)

def expected_path(name):
    return os.path.join(_expected_dir, name)

def result_path(name):
    if not os.path.isdir(_result_dir): os.makedirs(_result_dir)
    return os.path.join(_result_dir, name)

def input_data(filename):
    with open(input_path(filename)) as fh:
        return fh.read();
