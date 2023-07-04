## Pre-commit

This command enhances the content development experience, by running a variety of checks and linters.
It utilizes the [pre-commit|https://github.com/pre-commit/pre-commit] infrastructure, and uses a template file saved under the content repo (locally, or remotely) to dynamically generate a `pre-commit-config.yaml` file, based on the content being run.

**Note**: An internet connection is required for using `demisto-sdk pre-commit`.
## Usage

### Manually, using git (recommended)
* In a terminal shell, change directory to the folder used as a content repo.
* Make sure you have the latest version of `demisto-sdk`.
* Run `demisto-sdk pre-commit`.

### In a GitHub Action
* Under the content repo, we have a GitHub Action that automatically runs `demisto-sdk pre-commit`, so it runs automatically after each commit.
* Make sure to set the `GITHUB_ACTIONS` environment variable to `true`.

### Automatically, as a git hook
* Create a [git hook](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks) that calls `demisto-sdk pre-commit`.

## Steps

### External tools
#### [Ruff](https://github.com/astral-sh/ruff)
Runs Ruff, the extremely fast python linter, using the python version used in the container image set for the content item.

This step uses the Ruff rules configured in the `pyproject.toml` at the root of the content repo. If such does not exist, it uses Ruff's default rules.
The rules set under the official demisto/content repo [pyprojet.toml|https://github.com/demisto/content/blob/master/pyproject.toml] file were handpicked to ensure a high level of code quality, and prevent bugs often found in content.

This step may modify files (using Ruff's `--fix` flag). When files are modified, the step will fail, we recommend committing them into the repo.

#### Check JSON/YAML/AST(py)
Makes sure files in these extensions are in a proper structure.

#### [Autopep8](https://github.com/hhatto/autopep8)
A linter that automatically formats Python code to conform to the [PEP 8|https://peps.python.org/pep-0008/] style guide.

#### [Pycln](https://github.com/hadialqattan/pycln)
Pycln is a formatter for finding and removing unused import statements.


### SDK Commands
The following SDK commands are automatically run. See their respective docs for more information.
- validate
- run-unit-tests
- format
- secrets
