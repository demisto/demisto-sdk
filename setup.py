#!/usr/bin/env python3
# coding: utf-8

"""
    Demisto SDK
"""
import json
from pathlib import Path
from typing import List

from setuptools import find_packages, setup  # noqa: H301

NAME = "demisto-sdk"


# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

# Converting Pipfile to requirements style list because setup expects requirements.txt file.
def get_requirements(path: Path = Path(__file__).parent / 'Pipfile.lock', key='default') -> List[str]:
    """Converts Pipfile.lock to list of requirements"""
    with path.open(encoding='utf8') as stream:
        packs = json.load(stream)[key]
    parsed_packs = [f'{pack}{value["version"]}{"; " + value["markers"] if value.get("markers") else ""}'
                    for pack, value in packs.items()]
    return parsed_packs


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
    keywords=["Demisto", "Cortex XSOAR"],
    install_requires=get_requirements(),
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
