[![CircleCI](https://circleci.com/gh/demisto/demisto-sdk/tree/master.svg?style=svg)](https://circleci.com/gh/demisto/demisto-sdk/tree/master)

# Demisto SDK 

The Demisto SDK library can be used to manage your Demisto content with ease and efficiency.
The library uses python 3.7+.

## Usage

### Installation

`pip install demisto-sdk`

### CLI
You can use the SDK in the CLI as follows:
`demisto_sdk <action> <args>`. For more information, run `demisto_sdk -h`.

#### Examples:

`demisto_sdk extract -i Integrations/integration-MyInt.yml -o Integrations/MyInt -m` 
will split the yml file to a directory with the integration components (code, image, description, pipfile etc.)

`demisto_sdk unify -i Integrations/MyInt -o Integrations` will grab the integration components and unify them to a single yaml file.

`demisto_sdk validate` will validate your content files.


### In the code
You can import the SDK core class in your python code as follows:

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
  
## Contributing
## Push changes to GitHub

The Demisto SDK is MIT Licensed and accepts contributions via GitHub pull requests.
If you are a first time GitHub contributor, please look at these links explaining on how to create a Pull Request to a GitHub repo:
* https://guides.github.com/activities/forking/
* https://help.github.com/articles/creating-a-pull-request-from-a-fork/

**Working on your first Pull Request?** You can learn how from this *free* series [How to Contribute to an Open Source Project on GitHub](https://egghead.io/series/how-to-contribute-to-an-open-source-project-on-github)

## Contributor License Agreement
Before merging any PRs, we need all contributors to sign a contributor license agreement. By signing a contributor license agreement, we ensure that the community is free to use your contributions.

When you contribute a new pull request, a bot will evaluate whether you have signed the CLA. If required, the bot will comment on the pull request, including a link to accept the agreement. The CLA document is available for review as a [PDF](cla.pdf).

If the `license/cla` status check remains on *Pending*, even though all contributors have accepted the CLA, you can recheck the CLA status by visiting the following link (replace **[PRID]** with the ID of your PR): https://cla-assistant.io/check/demisto/demisto-sdk?pullRequest=[PRID] .


If you have a suggestion or an opportunity for improvement that you've identified, please open an issue in this repo.
Enjoy and feel free to reach out to us on the [DFIR Community Slack channel](http://go.demisto.com/join-our-slack-community), or at [info@demisto.com](mailto:info@demisto.com).
