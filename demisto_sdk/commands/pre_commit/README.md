## Pre-commit

### Overview

This command enhances the content development experience, by running a variety of checks and linters.
It utilizes the [pre-commit](https://github.com/pre-commit/pre-commit) framework.
A `.pre-commit-config-template.yaml` file is used to configure the hooks (if found in the content repo. Otherwise, a [default](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/pre_commit/.pre-commit-config_template.yaml) is used)

Since content items are made to run in containers with different Python versions and dependencies, this command matches content items with suitable configurations, before passing the generated (temporary) `.pre-commit-config.yaml` file.

**Note**: An internet connection is required for this command.

### Options
* **-i, --input, --files**
The paths to run pre-commit on. May pass multiple paths.
* **--staged-only**
Whether to run only on staged files.
* **--commited-only**
Whether to run on committed files only.
* **-g, --git-diff**
Whether to use git to determine which files to run on.
* **--prev-ver**
The previous version to compare against. If not provided, the previous version will be determined using git.
* **-a, --all-files**
Whether to run on all files.
* **--mode**
Special mode to run the pre-commit with.
* **--skip**
A list of precommit hooks to skip.
* **--validate/--no-validate**
Whether to run demisto-sdk validate or not.
* **--format/--no-format**
Whether to run demisto-sdk format or not.
* **--secrets/--no-secrets**
Whether to run demisto-sdk secrets or not.
* **-v, --verbose**
Verbose output of pre-commit.
* **--show-diff-on-failure**
Show diff on failure.
* **--dry-run**
Whether to run the pre-commit hooks in dry-run mode, which will only create the config file.
* **--docker/--no-docker**
Whether to run docker based hooks or not.
* **--image-ref**
The docker image reference to run docker hooks with. Overrides the docker image from YAML or native image config.
* **--docker-image**
Override the `docker_image` property in the template file. This is a comma separated list of: `from-yml`, `native:dev`, `native:ga`, `native:candidate`.
* **--console-log-threshold**
Minimum logging threshold for the console logger.
* **--file-log-threshold**
Minimum logging threshold for the file logger.
* **--log-file-path**
Path to save log files onto.
* **--template-path**
A custom path for pre-defined pre-commit template, if not provided will use the default template.

### Usage

#### Manually Running
* In a terminal shell, change the directory to the folder that is used as a the content repo.
* Run `demisto-sdk pre-commit`.

#### Automatically, as a git hook
* Create a [git hook](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks) that runs `demisto-sdk pre-commit`.

### Modes
You can set different arguments for different modes. for example, some rules should be excluded in the nightly build.
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

### Hooks
Hooks can be set in the `.pre-commit-config_template.yaml` file. The syntax is similar to the official [`pre-commit` hooks](https://pre-commit.com/#new-hooks). But the command allows more keys to be set:

### Skip key
In order to skip certain hook from running, you can add a `skip` key to the hook configuration.
```yaml
- id: sample-hook
  skip: true
```
This key could be use together with [mode](#modes), to skip certain hook when running in a specific mode.

### Needs key
Needs keys allow to define dependencies between hooks. If a hook with `needs` is skipped, hooks that depend on it will also be skipped.
In this example, both hooks will be skipped.
```yaml
- id: sample-hook
  skip: true
- id: needs-example
  needs: ["sample-hook"]
```

### parallel key
The parallel key indicates whether a hook should run in parallel, by default hooks such as mypy, ruff and docker produce multiple hooks which run in parallel.
Default is True. In order to avoid running a specific hook in parallel you can set it to `false`. When setting the parallel of a hook to `false`, a split hook will run sequentially.
```yaml
- id: sample-hook
  parallel: false
```

### Steps

#### External tools
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

### Docker hooks
To run a command in a script's relevant container you can set up a Docker Hook.

A docker hook must be under the `local` repo, and it's `id` must end with `in-docker`.

#### Example
```yaml
  - id: simple-in-docker
    name: simple-in-docker
    description: my simple description
    entry: simplelinter
    args: ['run-all-checks']
```

The `entry` key should be the command that should be run (eg. pylint, pytest).

#### The env key
Some commands require environment variables to be set. To configure environment variables for docker hooks you can set the `env` key. Here is an example with pytest.
```yaml
  - id: simple-in-docker
    env:
      DEMISTO_SDK__PYTEST__TESTS_PATH: Tests/scripts
```

#### The copy_files key
Some hooks require several files to exist in the same directory as the code file in order to run properly. To configure this you can set the `copy_files` key as follows:
```yaml
- id: simple-in-docker
  copy_files:
    - Tests/scripts/conftest.py
```

#### The config_file_arg key
Often with commands we run in the docker we have a configuration file that is specified per Integration/Script. To configure this you can set the `config_file_arg` key as follows. The configuration file should be in the same directory as the code file. Here is an example with ruff.
```yaml
  - id: simple-in-docker
    config_file_arg:
      arg_name: '--config'
      file_name: 'ruff.toml'
```
### Examples:

`demisto-sdk --pre-commit`
Will run pre-commit on all files collected by git.

`demisto-sdk --pre-commit -i Packs/hello_world`
Will run pre-commit on all files in pack hello_world.


`demisto-sdk --pre-commit --no-validate`
Will run pre-commit without the validate step.

`demisto-sdk --pre-commit --show-diff-on-failure`
Will run pre-commit and show differences when failing.
