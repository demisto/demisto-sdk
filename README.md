# Demisto SDK 

The Demisto SDK library can be used to manage your Demisto content with ease and efficiency.

## Usage

### Installation

`pip install demisto-sdk`

### CLI
You can use the SDK in the CLI as follows:
`demisto_sdk <action> <args>`. For more information, run `demisto_sdk -h`.

### In the code
You can import the SDK core class in your code as follows:

`from demisto_sdk.core import DemistoSDK`

## Dev Environment Setup
We build for python 3.7 and 3.8. We use [tox](https://github.com/tox-dev/tox) for managing environments and running unit tests.

Install `tox`:
```
pip install tox
```
List configured environments:
```
tox -l
```
Then setup dev virtual envs for python 3 (will also install all necessary requirements):
```
tox --devenv venv3 --devenv py37
```


## Running Unit Tests
We use pytest to run unit tests. Inside a virtual env you can run unit test using:
```
python -m pytest -v
```
Additionally, our build uses tox to run on multiple envs. To use tox to run on all supported environments (py37, py38), run:
```
tox -q  
```
To run on a specific environment, you can use:
```
tox -q -e py37
```


## License
MIT - See [LICENSE](LICENSE) for more information.
   