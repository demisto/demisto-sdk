#!/usr/bin/env python3
# coding: utf-8

"""
    Demisto SDK
"""
import configparser

from setuptools import find_packages, setup  # noqa: H301

NAME = "demisto-sdk"
# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

# Converting Pipfile to requirements style list because setup expects requirements.txt file.
parser = configparser.ConfigParser()
parser.read("Pipfile")


def end_or_comment_index(value: str):
    return len(value) if value.find("#") == -1 else value.find("#")


# when install local version for development, demisto-sdk gets added to the pipfile and should be ignored here
install_requires = [f'{key}{value[:end_or_comment_index(value)]}'.replace('\'', '').replace('\"', '').replace('*', '')
                    for key, value in parser['packages'].items() if key != 'demisto-sdk']

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
    install_requires=install_requires,
    packages=find_packages(
        exclude=["*.tests.*", "*.tests"]
    ),
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
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: Implementation :: CPython'
    ],
    python_requires=">=3.7",
    author="Demisto"
)
