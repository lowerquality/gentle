import logging
import os
import yaml

from util.paths import get_resource, ENV_VAR
from gentle import metasentence

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Config:
    __metaclass__ = Singleton
    def __init__(self):
        self.config = {
            'samplerate': 8000,
            'silencephones': '1:2:3:4:5:6:7:8:9:10',
            'context-width': '3'}

    def load(self, configFileName):
        with open(configFileName, 'r') as f:
            self.config = yaml.safe_load(f)

    def __getitem__(self, key):
        return self.config.__getitem__(key)

class Resources:
    def __init__(self, modelDir):
        self.proto_langdir = get_resource(modelDir)
        self.nnet_gpu_path = get_resource(os.path.join(modelDir, 'online'))
        self.full_hclg_path = get_resource(os.path.join(self.nnet_gpu_path, 'graph', 'HCLG.fst'))

        self.config = Config()
        confPath = os.path.join(self.proto_langdir, 'config.yaml')
        if os.path.exists(confPath):
            self.config.load(confPath)

        def require_dir(path):
            if not os.path.isdir(path):
                raise RuntimeError("No resource directory %s.  Check %s environment variable?" % (path, ENV_VAR))


        require_dir(self.proto_langdir)
        require_dir(self.nnet_gpu_path)

        with open(os.path.join(self.proto_langdir, "langdir", "words.txt")) as fh:
            self.vocab = metasentence.load_vocabulary(fh)

    def getConfig(self):
        return self.config

if __name__ == '__main__':
    resources = Resources('exp')
    config1 = resources.getConfig()
    config2 = Config('')
    print config1['samplerate'], config2['silencephones']

