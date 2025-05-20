# Demisto SDK

[![PyPI version](https://badge.fury.io/py/demisto-sdk.svg)](https://badge.fury.io/py/demisto-sdk)
[![CircleCI](https://circleci.com/gh/demisto/demisto-sdk/tree/master.svg?style=svg)](https://circleci.com/gh/demisto/demisto-sdk/tree/master)
[![Coverage Status](https://coveralls.io/repos/github/demisto/demisto-sdk/badge.svg?branch=master)](https://coveralls.io/github/demisto/demisto-sdk?branch=master)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v1.json)](https://github.com/charliermarsh/ruff)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

The Demisto SDK is a Python library designed to aid the development process, both to validate entities being developed and to assist in the interaction between your development setup and Cortex XSOAR or Cortex XSIAM.

Requirements:

- Python 3.9, 3.10 or 3.11.
- git installed.
- A linux, mac or WSL2 machine.

Windows machines are not supported - use WSL2 or run in a container instead.

## Usage

### Installation

- **Install** - `pip3 install demisto-sdk`
- **Upgrade** - `pip3 install --upgrade demisto-sdk`

### Environment Variable Setup
**Connect demisto-sdk with Cortex XSOAR server** - Some SDK commands require you to have an interaction with the Cortex XSOAR or Cortex XSIAM server. Examples of such interactions
include uploading and downloading entities to or from XSOAR or XSIAM and running commands in the CLI.

To use these functions, Set the following environment variables, or place an [.env file](https://pypi.org/project/python-dotenv/) at the root of the content pack:

#### For Cortex XSOAR 6.x Only
 1. Get your API key by going to the Cortex XSOAR server -> `Settings` -> `Integrations` -> `API Keys` -> `Get Your Key` -> Give your key a name and press `Generate Key`.
 2. Copy the given key.
 3. Add the following parameters to `~/.zshrc` and `~/.bash_profile`:

    ```bash
    export DEMISTO_BASE_URL=<http or https>://<demisto-server url or ip>:<port>
    export DEMISTO_API_KEY=<API key>
    ```

#### For Cortex XSIAM or Cortex XSOAR 8.x and above
1. The base URL should be retrieved from the XSIAM instance by navigating to `Settings` -> `Configurations` -> `API Keys` -> clicking on the `Copy URL` button located at the top right corner of the page, and not the browser URL.
2. The API key should be set to a Standard security level and must have the Instance Administrator role.
3. The `XSIAM_AUTH_ID` environment variable needs to be set. Get it from the `ID` column of the created API Key.
4. Add the following parameters to `~/.zshrc` and `~/.bash_profile`:

    ```bash
    export DEMISTO_BASE_URL=<BASE_URL>
    export DEMISTO_API_KEY=<API_KEY>
    export XSIAM_AUTH_ID=<THE_XSIAM_AUTH_ID>
    ```

- Please note that once the `XSIAM_AUTH_ID` environment variable is set, the SDK commands will be configured to work with a Cortex XSIAM / XSOAR 8.x instance.
In order to set Demisto SDK to work with a Cortex XSOAR 6.x instance, you need to delete the `XSIAM_AUTH_ID` parameter from your environment. To do this, please run the following command:
    ```bash
    unset XSIAM_AUTH_ID
    ```


- In case the primary git branch is not **master**, or the upstream is not named **origin**, set them with environment variables:
    ```bash
    export DEMISTO_DEFAULT_BRANCH = <branch name here>
    export DEMISTO_DEFAULT_REMOTE = <upstream name here>
    ```

    > For more configurations, check the [demisto-py](https://github.com/demisto/demisto-py) repo (the SDK uses demisto-py to communicate with Cortex XSOAR).

- For the **Validate** and **Format** commands to work properly:
      - Install node.js, and make sure `@mdx-js/mdx`, `fs-extra` and `commander` are installed in node-modules folder (`npm install ...`).
      - Set the `DEMISTO_README_VALIDATION` environment variable to True.

       MDX is used to validate markdown files, and make sure they render properly on XSOAR and [xsoar.pan.dev](https://xsoar.pan.dev).

- Reload your terminal.

---

### CLI usage

You can use the SDK in the CLI as follows:

```bash
demisto-sdk <command> <args>
```

For more information, run `demisto-sdk -h`.

For more information on a specific command execute `demisto-sdk <command> -h`.

### Content path

The **demisto-sdk** is made to work with Cortex content, structured similar to the [official Cortex content repo](https://github.com/demisto/content).

Demisto-SDK commands work best when called from the content directory or any of its subfolders.
To run Demisto-SDK commands from other folders, you may set the `DEMISTO_SDK_CONTENT_PATH` environment variable.

We recommend running all demisto-SDK commands from a folder with a git repo, or any of its subfolders. To suppress warnings about running commands outside a content repo folder, set the `DEMISTO_SDK_IGNORE_CONTENT_WARNING` environment variable.

### Version Check

`demisto-sdk` will check against the GitHub repository releases for a new version every time it runs and will issue a warning if you are not using the latest and greatest. If you wish to skip this check you can set the environment variable: `DEMISTO_SDK_SKIP_VERSION_CHECK`. For example:

```bash
export DEMISTO_SDK_SKIP_VERSION_CHECK=yes
```

### Run using Docker image

You can run the Demisto-SDK using a docker image. For more details go to [Demisto-SDK Docker](./docs/create_command.md).

---

## Commands

Supported commands:

1. [init](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/init/README.md)
2. [Validate](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/validate/README.md)
3. [Pre-Commit](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/pre_commit/README.md)
4. [Secrets](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/secrets/README.md)
5. [Prepare-Content](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/prepare_content/README.md#prepare-content)
6. [Split](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/split/README.md)
7. [Format](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/format/README.md)
8. [Run](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/run_cmd/README.md)
9. [Run-playbook](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/run_playbook/README.md)
10. [Upload](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/upload/README.md)
11. [Download](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/download/README.md)
12. [Generate-docs](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/generate_docs/README.md)
13. [Generate-test-playbook](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/generate_test_playbook/README.md)
14. [Generate-outputs](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/generate_outputs/README.md)
15. [Update-release-notes](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/update_release_notes/README.md)
16. [Zip-packs](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/zip_packs/README.md)
17. [openapi-codegen](https://xsoar.pan.dev/docs/integrations/openapi-codegen)
18. [postman-codegen](https://xsoar.pan.dev/docs/integrations/postman-codegen)
19. [generate-integration](https://xsoar.pan.dev/docs/integrations/code-generator)
20. [generate-yml-from-python](https://xsoar.pan.dev/docs/integrations/yml-from-python-code-gen)
21. [generate-unit-tests](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/generate_unit_tests/README.md)
22. [setup-env](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/setup_env/README.md)

---

### Logs

Log files are generated and stored automatically by default in the user's home directory:  
**Linux / macOS**: `$HOME/.demisto-sdk/logs`  
**Windows**: `%USERPROFILE%\.demisto-sdk\logs`  

The default directory can be overriden using the `--log-file-path` flag, or the `DEMISTO_SDK_LOG_FILE_PATH` environment variable.

---

### Customizable command configuration

You can create your own configuration for the `demisto-sdk` commands by creating a file named `.demisto-sdk-conf` within the directory from which you run the commands.
This file will enable you to set a default value to the existing command flags that will take effect whenever the command is run.
This can be done by entering the following structure into the file:

```INI
[command_name]
flag_name=flag_default_value
```

Note: Make sure to use the flag's full name and input `_` instead of a `-` if it exists in the flag name (e.g. instead of `no-docker-checks` use `no_docker_checks`).

Here are a few examples:

- As a user, I would like to include untracked git files in my validation when running the `validate` command. In the `.demisto-sdk-conf` file I'll enter:

   ```INI
   [validate]
   include_untracked=true
   ```

- As a user, I would like to automatically use minor version changes when running the `update-release-notes` command. In the `.demisto-sdk-conf` file I'll enter:

   ```INI
   [update-release-notes]
   update_type=minor
   ```

---

## License

MIT - See [LICENSE](LICENSE) for more information.

---

## How to setup a development environment?

Follow the guide found [here](CONTRIBUTION.md#2-install-demisto-sdk-dev-environment) to setup your `demisto-sdk` dev environment.
The development environment is connected to the branch you are currently using in the SDK repository.

---

## Contributions

Contributions are welcome and appreciated.
For information regarding contributing, press [here](CONTRIBUTION.md).

---

## Internet Connection

An internet connection is required for the following commands to work properly:

1. [Format](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/format/README.md)
2. [Validate](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/validate/README.md)
3. [Update-release-notes](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/update_release_notes/README.md)
4. [Pre-commit](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/pre_commit/README.md)

Note that the [Download](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/download/README.md) command will work only partially without an internet connection, it will fail when using the '-fmt, --run-format' argument.

- When working offline (or in an airgapped environment), set the `DEMISTO_SDK_OFFLINE_ENV` environment variable to `true`:

   ```bash
   export DEMISTO_SDK_OFFLINE_ENV=TRUE
   ```

   When set, Demisto-SDK features requiring an internet connection will not be run, often saving some time and avoiding errors.

---

## Docker Usage

Docker is required to run certain commands.

The following command requires Docker:

1. [setup-env](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/setup_env/README.md)

However, some commands can be executed partially without Docker:

1. [Format](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/format/README.md) - To run without Docker, use the `--no-graph` flag.
2. [Generate-docs](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/generate_docs/README.md) - To run without Docker, use the `--no-graph` flag.
3. [Validate](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/validate/README.md) - To skip Docker validation, use the `--no-docker-checks` flag.
4. [pre-commit](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/pre_commit/README.md) - To run without Docker hooks, use the `--no-docker` flag.

---

## XSOAR CI/CD

For information regarding XSOAR CI/CD, please see [this article](https://xsoar.pan.dev/docs/reference/packs/content-management)

## Custom Container Registry

By default, the `demisto-sdk` will use `dockerhub` as the container registry to pull the integrations and scripts docker image.
In order configure a custom container registry, the following environment variables must be set:

- `DEMISTO_SDK_CONTAINER_REGISTRY`: the URL of the container registry.
- `DEMISTO_SDK_CR_USER`: the username to use in the container registry.
- `DEMISTO_SDK_CR_PASSWORD`: the password to use in the container registry.
