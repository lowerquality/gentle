from setuptools import setup
from gentle import __version__

setup(
    app=['gentle.py'],
    data_files=[],
    options={'py2app': {
        'argv_emulation': False,
        'resources': 'standard_kaldi,ffmpeg,www,data,PROTO_LANGDIR'
    }},
    name='gentle',
    version=__version__,
    description='Robust yet lenient forced-aligner built on Kaldi.',
    url='http://lowerquality.com/gentle',
    author='Robert M Ochshorn',
    license='MIT',
    packages=['gentle'],
    install_requires=['twisted'],
    setup_requires=['nose>=1.0'],
)
