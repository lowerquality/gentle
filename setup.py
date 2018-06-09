from setuptools import setup
from gentle import __version__

setup(
    app=['serve.py'],
    data_files=[],
    options={'py2app': {
        'argv_emulation': False,
        'resources': 'k3,m3,ffmpeg,www,exp'
    }},
    name='gentle',
    version=__version__,
    description='Robust yet lenient forced-aligner built on Kaldi.',
    url='http://lowerquality.com/gentle',
    author='Robert M Ochshorn',
    license='MIT',
    packages=['gentle'],
    install_requires=['twisted'],
    test_suite='tests',
)
