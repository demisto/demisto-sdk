[![PyPI version](https://badge.fury.io/py/demisto-sdk.svg)](https://badge.fury.io/py/demisto-sdk)
[![CircleCI](https://circleci.com/gh/demisto/demisto-sdk/tree/master.svg?style=svg)](https://circleci.com/gh/demisto/demisto-sdk/tree/master)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/ppwwyyxx/OpenPano.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/demisto/demisto-sdk/context:python)


# Demisto SDK 

The Demisto SDK library can be used to manage your Demisto content with ease and efficiency.
The library uses python 3.7+.

## Usage

### Installation

`pip install demisto-sdk`

### CLI
You can use the SDK in the CLI as follows:
`demisto-sdk <action> <args>`. For more information, run `demisto-sdk -h`.

#### Examples:

`demisto-sdk extract -i Integrations/integration-MyInt.yml -o Integrations/MyInt -m` 
will split the yml file to a directory with the integration components (code, image, description, pipfile etc.)

`demisto-sdk unify -i Integrations/MyInt -o Integrations` will grab the integration components and unify them to a single yaml file.

`demisto-sdk validate` will validate your content files.


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
Contributions are welcome and appreciated.

## Development

You can read the following docs to get started:

[Development Guide](docs/development_guide.md)

[Validation Testing](docs/validation_testing.md)

## Push changes to GitHub

The Demisto SDK is MIT Licensed and accepts contributions via GitHub pull requests.
If you are a first time GitHub contributor, please look at these links explaining on how to create a Pull Request to a GitHub repo:
* https://guides.github.com/activities/forking/
* https://help.github.com/articles/creating-a-pull-request-from-a-fork/

**Working on your first Pull Request?** You can learn how from this *free* series [How to Contribute to an Open Source Project on GitHub](https://egghead.io/series/how-to-contribute-to-an-open-source-project-on-github)

## Review Process
A member of the team will be assigned to review the pull request. Comments will be provided by the team member as the review process progresses.

You will see a few [GitHub Status Checks](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/about-status-checks) that help validate that your pull request is according to our standards:

* **ci/circleci: build**: We use [CircleCI](https://circleci.com/gh/demisto/demisto-sdk) to run a full build on each commit of your pull request. The build will run our content validation hooks, linting and unit test. We require that the build pass (green build). Follow the `details` link of the status to see the full build UI of CircleCI.
* **LGTM analysis: Python**: We use [LGTM](https://lgtm.com) for continues code analysis. If your PR introduces new LGTM alerts, the LGTM bot will add a comment with links for more details. Usually, these alerts are valid and you should try to fix them. If the alert is a false positive, specify this in a comment of the PR.
* **license/cla**: Status check that all contributors have signed our contributor license agreement (see below). 


## Contributor License Agreement
Before merging any PRs, we need all contributors to sign a contributor license agreement. By signing a contributor license agreement, we ensure that the community is free to use your contributions.

When you contribute a new pull request, a bot will evaluate whether you have signed the CLA. If required, the bot will comment on the pull request, including a link to accept the agreement. The CLA document is available for review as a [PDF](docs/cla.pdf).

If the `license/cla` status check remains on *Pending*, even though all contributors have accepted the CLA, you can recheck the CLA status by visiting the following link (replace **[PRID]** with the ID of your PR): https://cla-assistant.io/check/demisto/demisto-sdk?pullRequest=[PRID] .


If you have a suggestion or an opportunity for improvement that you've identified, please open an issue in this repo.
Enjoy and feel free to reach out to us on the [DFIR Community Slack channel](http://go.demisto.com/join-our-slack-community), or at [info@demisto.com](mailto:info@demisto.com).
