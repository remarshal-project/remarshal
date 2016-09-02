#! /usr/bin/env python

import re
from setuptools import find_packages, setup

with open('remarshal.py', 'rb') as f:
    content = f.read().decode('utf-8')
    version = re.search(r"__version__ = '(\d+\.\d+\.\d+)",
                        content, re.MULTILINE).group(1)

setup(name='remarshal',
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
        'PyYAML >= 3.12',
    ],
    entry_points = {
        'console_scripts': ['remarshal = remarshal:main'],
    },
)
