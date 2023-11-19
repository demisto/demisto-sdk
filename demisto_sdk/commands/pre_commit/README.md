## Pre-commit

This command enhances the content development experience, by running a variety of checks and linters.
It utilizes the [pre-commit](https://github.com/pre-commit/pre-commit) infrastructure, and uses a template file saved under the content repo (locally, or remotely) to dynamically generate a `pre-commit-config.yaml` file, based on the content being run.

**Note**: An internet connection is required for using `demisto-sdk pre-commit`.
## Usage

### Manually, using git (recommended)
* In a terminal shell, change the directory to the folder that is used as a the content repo.
* Make sure you have the latest version of `demisto-sdk`.
* Run `demisto-sdk pre-commit`.

### In a GitHub Action
* Under the content repo, there is a GitHub Action that automatically runs `demisto-sdk pre-commit`, so it runs automatically after each commit.
* Make sure to set the `GITHUB_ACTIONS` environment variable to `true`.

### Automatically, as a git hook
* Create a [git hook](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks) that calls `demisto-sdk pre-commit`.

## Modes
When different args set for the different modes are needed, for example, some rules should be excluded in the nightly build.
Any key can be set this way.
You can set this as follows.
```yaml
  - id: sample-hook
    args:nightly: ['--exclude', '123']
    args:mode1: ['--test', '123']
    args: ['This is the default argument']
    otherkey:nightly: hello
    otherkey: world
```
And call precommit as follows: `demisto-sdk pre-commit -a --mode nightly`.
Note, that it is possible to use any mode that you like, and have multiple modes for each hook, like in the example.

## Steps

### External tools
#### [Ruff](https://github.com/astral-sh/ruff)
Runs Ruff, the extremely fast Python linter, using the Python version used in the container image set for the content item.

This step uses the Ruff rules configured in the `pyproject.toml` at the root of the content repo. If pyproject.toml does not exist, it uses Ruff's default rules.
The rules set under the official demisto/content repo [pyproject.toml](https://github.com/demisto/content/blob/master/pyproject.toml) file were handpicked to ensure a high level of code quality, and prevent bugs often found in content.

This step may modify files (using Ruff's `--fix` flag). When files are modified, the step will fail. We recommend committing them into the repo.

#### Check JSON/YAML/AST(py)
Makes sure files in these extensions are in a proper structure.

#### [Autopep8](https://github.com/hhatto/autopep8)
A linter that automatically formats Python code to conform to the [PEP 8|https://peps.python.org/pep-0008/] style guide.

#### [Pycln](https://github.com/hadialqattan/pycln)
Pycln is a formatter for finding and removing unused import statements.


### SDK Commands
The following SDK commands are automatically run
- [validate](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/validate/README.md)
- [format](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/format/README.md)
- [secrets](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/secrets/README.md)
- run-unit-tests: Runs the unit tests in an environment matching the content.

### Docker hooks
To run a command in a script's relevant container you can set up a Docker Hook.

A docker hook must be under the `local` repo and it's `id` must end with `in-docker`.

#### Example
```yaml
  - id: simple-in-docker
    name: simple-in-docker
    description: my simple description
    entry: simplelinter
    args: ['run-all-checks']
```

The `entry` key should be the command that should be run (eg. pylint, pytest).

#### The config_file_arg key
Often with commands we run in the docker we have a configuration file that is specified per Integration/Script. To configure this you can set the `config_file_arg` key as follows. The configuration file should be in the same directory as the code file. Here is an example with ruff.
```yaml
  - id: simple-in-docker
    config_file_arg:
      arg_name: '--config'
      file_name: 'ruff.toml'
```
