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
`demisto-sdk <command> <args>`.
For more information, run `demisto-sdk -h`.
For more information on a specific command execute `demisto-sdk <command> -h`.


## Commands

### Unify

Unify code, image and description files to a single Demisto yaml file.
**Arguments**:
* *-i INDIR, --indir INDIR*
  The path to the directory in which the files reside
* *-o OUTDIR, --outdir OUTDIR*
  The path to the directory into which to write the unified yml file

**Examples**:
`demisto-sdk unify -i Integrations/MyInt -o Integrations`
This will grab the integration components and unify them to a single yaml file.

### Extract

Extract code, image and description files from a demisto integration or script yml file.
**Arguments**:
* *-i INFILE, --infile INFILE*
                        The yml file to extract from
* *-o OUTFILE, --outfile OUTFILE*
                        The output file or dir (if doing migrate) to write the
                        code to
* *-m, --migrate*
                        Migrate an integration to package format. Pass to -o
                        option a directory in this case.
* *-t {script,integration}, --type {script,integration}*
                        Yaml type. If not specified will try to determine type
                        based upon path.
* *-d {True,False}, --demistomock {True,False}*
                        Add an import for demisto mock, true by default
* *-c {True,False}, --commonserver {True,False}*
                        Add an import for CommonServerPython. If not specified
                        will import unless this is CommonServerPython

**Examples**:
`demisto-sdk extract -i Integrations/integration-MyInt.yml -o Integrations/MyInt -m`
This will split the yml file to a directory with the integration components (code, image, description, pipfile etc.)

### Validate

Validate your content files.
**Arguments**:
* *-c CIRCLE, --circle CIRCLE*
                        Is CircleCi or not
* *-b BACKWARD_COMP, --backward-comp BACKWARD_COMP*
                        To check backward compatibility.
* *-t TEST_FILTER, --test-filter TEST_FILTER*
                        Check that tests are valid.
* *-j, --conf-json*
                        Validate the conf.json file.
* *-i, --id-set*
                        Create the id_set.json file.
* *-p PREV_VER, --prev-ver PREV_VER*
                        Previous branch or SHA1 commit to run checks against.
* *-g, --use-git*
                        Validate changes using git.

**Examples**:
`demisto-sdk validate`
This will validate your content files.

### Lint

Run lintings (flake8, mypy, pylint, bandit) and pytest. pylint and pytest will run within the docker image of an integration/script. Meant to be used with integrations/scripts that use the folder (package) structure. Will lookup up what docker image to use and will setup the dev dependencies and file in the target folder.
**Arguments**:
* *-d DIR, --dir DIR*
  Specify directory of integration/script (default: None)
* *--no-pylint*
  Do NOT run pylint linter (default: False)
* *--no-mypy*
  Do NOT run mypy static type checking (default: False)
* *--no-flake8*
  Do NOT run flake8 linter (default: False)
* *--no-bandit*
  Do NOT run bandit linter (default: False)
* *--no-test*
  Do NOT test (skip pytest) (default: False)
* *-r, --root*
  Run pytest container with root user (default: False)
* *-k, --keep-container*
  Keep the test container (default: False)
* *-v, --verbose*
  Verbose output (default: False)
* *--cpu-num CPU_NUM*
  Number of CPUs to run pytest on (can set to `auto` for automatic detection of the number of CPUs.) (default: 0)

**Examples**:
`demisto-sdk lint -d Integrations/PaloAltoNetworks_XDR --no-mypy`
This will run the linters, excluding mypy, on the python files inside the "Integrations/PaloAltoNetworks_XDR" directory.

### Secrets

Run Secrets validator to catch sensitive data before exposing your code to public repository. Attach full path to whitelist to allow manual whitelists. Default file path to secrets is "./Tests/secrets_white_list.json".
**Arguments**:
* *-c CIRCLE, --circle CIRCLE*
                        Is CircleCi or not (default: False)
* *-wl WHITELIST, --whitelist WHITELIST*
                        Full path to whitelist file, file name should be "secrets_white_list.json" (default: ./Tests/secrets_white_list.json)

**Examples**:
`demisto-sdk secrets`
This will run the secrets validator on your files.

### Create

Create content artifacts.
**Arguments**:
* *-a ARTIFACTS_PATH, --artifacts_path ARTIFACTS_PATH*
                        The path of the directory in which you want to save
                        the created content artifacts
* *-p, --preserve_bundles*
                        Flag for if you'd like to keep the bundles created in
                        the process of making the content artifacts

**Examples**:
`demisto-sdk create -a .`
This will create content artifacts in the current directory.


## In the code
You can import the SDK core class in your python code as follows:

`from demisto_sdk.core import DemistoSDK`

## Dev Environment Setup
We build for python 3.7 and 3.8. We use [tox](https://github.com/tox-dev/tox) for managing environments and running unit tests.

1) Clone the Demisto-SDK repository (Make sure that you have GitHub account):\
`git clone https://github.com/demisto/demisto-sdk`

2) **If you are using a default python version 3.7 or 3.8 you can skip this part.**

    [pyenv](https://github.com/pyenv/pyenv) is an easy tool to control the versions of python on your environment.
[Install pyenv](https://github.com/pyenv/pyenv#installation) and then run:
    ```
    pyenv install 3.7.5
    pyenv install 3.8.0
    ```
    After installing run in `{path_to_demisto-sdk}/demisto-sdk`:
    ```
    cd {path_to_demisto-sdk}/demisto-sdk
    pyenv versions
    ```
    And you should see marked with asterisks:
    ```
    * 3.7.5 (set by /{path_to_demisto-sdk}/demisto-sdk/.python-version)
    * 3.8.0 (set by /{path_to_demisto-sdk}/demisto-sdk/.python-version)
    ```

    If not, simply run the following command from the Demisto-SDK repository:
    ```
    pyenv local 3.7.5 3.8.0
    ```

3) Using the terminal go to the Demisto-SDK repository - we will set up the development environment there.

4) Install `tox`:
    ```
    pip install tox
    ```
    Then setup dev virtual envs for python 3 (will also install all necessary requirements):
    ```
    tox
    ```
5) Set your IDE to use the virtual environment you created using the following path:
`/{path_to_demisto-sdk}/demisto-sdk/.tox/py37/bin/python`

### How to run commands in your development environment
In the Demisto-SDK repository while on the git branch you want to activate and run this command to use python 3.7:
 ```
 source .tox/py37/bin/activate
  ```
  or this command to use python 3.8:
   ```
 source .tox/py38/bin/activate
 ```
While in the virtual environment, you can use the ```demisto-sdk``` commands with all the changes made in your local environment.

In case your local changes to `demisto-sdk` are not updated, you need to update your `tox` environment
by running this command from the Demisto-SDK repository:
```angular2
tox -e {your_env}
```
where {your_env} is py37 or py38.

## Running git hooks
We use are using [pre-commit](https://pre-commit.com/) to run hooks on our build. To use it run:
```bash
pre-commit install
```
It is recommended to run ```pre-commit autoupdate``` to keep hooks updated.

## Running Unit Tests
To run all our unit tests we use: `tox` on all envs.

For additional verbosity use: `tox -vv`

To run `tox` without verbosity run: `tox -q`

To run on a specific environment, you can use: `tox -q -e py37`

To run a specific test run: `pytest -vv tests/{test_file}.py::{TestClass}::{test_function}`

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
