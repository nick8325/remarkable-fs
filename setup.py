#!/usr/bin/env python

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='remarkable-fs',
    version='0.1',
    description='A FUSE filesystem driver for the reMarkable tablet',
    long_description=long_description,
    url='https://github.com/nick8325/remarkable-fs',
    author='Nick Smallbone',
    author_email='nick@smallbone.se',

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Topic :: System :: Hardware',
        'Topic :: System :: Filesystems',
        'Topic :: Utilities',
    ],

    keywords='remarkable fuse',

    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=['fusepy', 'paramiko', 'lazy', 'progress', 'fpdf'],

    entry_points={
        'console_scripts': [
            'remarkable-fs=remarkable_fs:main',
        ],
    },
)
