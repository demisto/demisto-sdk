#!/usr/bin/env python3
# coding: utf-8

"""
    Demisto SDK
"""
import toml
import configparser
from setuptools import find_packages, setup  # noqa: H301

NAME = "demisto-sdk"
REQUIREMENTS_NAME = 'requirements.txt'
# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools
parser = configparser.ConfigParser()
parser.read("Pipfile")

packages = "packages"
al = []
for key in parser[packages]:
    value = parser[packages][key]
    al.append(key + value.replace("\"", "") + "\n")

with open('README.md', 'r') as f:
    readme = f.read()

setup(
    use_scm_version={
        'local_scheme': lambda a: ""
    },
    setup_requires=['setuptools_scm'],
    name=NAME,
    description="A Python library for the Demisto SDK",
    author_email="",
    url="https://github.com/demisto/demisto-sdk",
    keywords=["Demisto"],
    install_requires=al,
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': ['demisto-sdk = demisto_sdk.__main__:main']
    },
    long_description=readme,
    long_description_content_type='text/markdown',
    license='MIT',
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython'
    ],
    python_requires=">=3.7",
    author="Demisto"
)
