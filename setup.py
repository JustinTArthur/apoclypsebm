#!/usr/bin/env python
from setuptools import setup, find_packages

from apoclypsebm.detect import LINUX
from apoclypsebm.version import VERSION

try:
    import py2exe
except ImportError:
    py2exe = None

args = {
    'name': 'apoclypsebm',
    'version': VERSION,
    'description': 'The ApoCLypse Bitcoin Miner',
    'long_description': open('README.md').read(),
    'long_description_content_type': 'text/markdown',
    'author': 'Justin T. Arthur',
    'author_email': 'justinarthur@gmail.com',
    'url': 'https://github.com/JustinTArthur/apoclypsebm/',
    'install_requires': ["pyopencl>=2017.2,<=2020.1", 'pyserial>=2.6', 'PySocks>=1.6.0'],
    'entry_points': {
        'console_scripts': (
            'apoclypse = apoclypsebm.command:main',
        ),
    },
    'packages': find_packages(include=('apoclypsebm', 'apoclypsebm.*',)),
    'package_data': {'apoclypsebm': ('apoclypse-0.cl', 'apoclypse-loopy.cl')},
    'python_requires': '>=3.6',
    'classifiers': ('License :: Public Domain',)
}

if LINUX:
    args['install_requires'].append('pyudev>=0.16')

if py2exe:
    args.update({
        # py2exe options
        'options': {
            'py2exe': {
                'optimize': 2,
                'bundle_files': 2,
                'compressed': True,
                'dll_excludes': ('OpenCL.dll', 'w9xpopen.exe', 'boost_python-vc90-mt-1_39.dll'),
                'excludes': ("Tkconstants", "Tkinter", "tcl", "curses", "_ssl", "pyexpat", "unicodedata", "bz2"),
            },
        },
        'package_data': {'apoclypsebm': ('apoclypse-0.cl', 'apoclypse-loopy.cl')},
        'zipfile': None
    })

setup(**args)
