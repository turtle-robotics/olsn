# -*- coding: utf-8 -*-

"""
BITalino Python API

Setup for package installation.

Created on Nov 27 11:25:00 2013

@author: Carlos Carreiras

"""

import re
from setuptools import setup


def readme():
    with open('README.rst', 'r', encoding='utf-8') as f:
        description = f.read()
    return description


def getVersion():
    VERSIONFILE = 'bitalino/_version.py'
    with open(VERSIONFILE, 'rt', encoding='utf-8') as f:
        verstrline = f.read()
    VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
    mo = re.search(VSRE, verstrline, re.M)
    if mo:
        verstr = mo.group(1)
    else:
        raise RuntimeError("Unable to find version string in %s." % (VERSIONFILE,))
    return verstr


setup(
    name='bitalino',
    version=getVersion(),
    packages=['bitalino'],
    python_requires='>=3.6',
    install_requires=['numpy>=1.16', 'pyserial>=3.4'],
    url='http://www.bitalino.com',
    license='GPL',
    author='Team BIT',
    author_email='bitalino@plux.info',
    description='BITalino Python API.',
    long_description=readme(),
    keywords='BITalino, Physiological Computing, Biosignal, EDA, ECG, EMG, Accelerometer',
    classifiers=['Development Status :: 3 - Alpha',
                 'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.8',
                 'Programming Language :: Python :: 3.9',
                 'Programming Language :: Python :: 3.10',
                 'Programming Language :: Python :: 3.11',
                 'Programming Language :: Python :: 3.12',
                 'Topic :: Scientific/Engineering'],
    zip_safe=False
)
