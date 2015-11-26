from setuptools import setup

setup(
    app=['gentle.py'],
    data_files=[],
    options={'py2app': {
        'argv_emulation': False,
        'resources': 'standard_kaldi,mkgraph,ffmpeg,www,data,PROTO_LANGDIR'
    }},
    name='gentle',
    version='0.1',
    description='Robust yet lenient forced-aligner built on Kaldi.',
    url='http://lowerquality.com/gentle',
    author='Robert M Ochshorn',
    license='MIT',
    packages=['gentle'],
    install_requires=['twisted', 'wxPython'],
    setup_requires=['py2app'],
)
