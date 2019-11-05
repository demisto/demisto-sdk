# coding: utf-8

"""
    Demisto SDK
"""

from setuptools import setup, find_packages  # noqa: H301

NAME = "demisto-sdk"

# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = [
    "python-dateutil>=2.5.3",
    "six>=1.10",
    "urllib3>=1.23",
    "tzlocal>=2.0.0",
]

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
    install_requires=REQUIRES,
    packages=find_packages(),
    include_package_data=True,
    long_description=readme,
    long_description_content_type='text/markdown',
    license='MIT',
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython'
    ],
)