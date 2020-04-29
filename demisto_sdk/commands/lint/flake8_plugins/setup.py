from setuptools import find_packages, setup

setup(
    name='flake8-demisto',
    version='1.0.0',
    packages=find_packages(),
    entry_points={
        'flake8.extension': [
            'D100 = flake8_demistosdk.checker:direct_dict_key_access',
        ],
    }
)
