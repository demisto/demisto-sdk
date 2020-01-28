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
