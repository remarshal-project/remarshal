#! /usr/bin/env python

import os.path
import re
from setuptools import find_packages, setup

remarshal_file = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'remarshal.py'
)
with open(remarshal_file, 'rb') as f:
    content = f.read().decode('utf-8')
    version = re.search(
        r"__version__ = '(\d+\.\d+\.\d+)",
        content, re.MULTILINE
    ).group(1)

formats = ['json', 'toml', 'msgpack', 'yaml']

setup(
    name='remarshal',
    version=version,
    description='Convert between TOML, YAML and JSON',
    author='dbohdan',
    url='https://github.com/dbohdan/remarshal',
    license='MIT',
    py_modules=['remarshal'],
    test_suite='tests',
    install_requires=[
        'python-dateutil >= 2.5.0',
        'pytoml >= 0.1.11',
        'PyYAML >= 5.1',
        'u-msgpack-python >= 2.5.1',
    ],
    entry_points={
        'console_scripts': [
            'remarshal = remarshal:main'
        ] + [
            '{0}2{1} = remarshal:main'.format(x, y)
            for x in formats for y in formats
        ]
    },
)
