## Setup Environment

### Overview

The setup-env command creates a content environment and integration/script environment.
The command will configure VSCode and XSOAR/XSIAM instances for development and testing.
### Options

- **--ide**: IDE type to configure the environment for. If not specified, the IDE will be auto-detected. Case-insensitive.
  - Default: `auto-detect`

- **--input**: Paths to content integrations or script to setup the environment. If not provided, will configure the environment for the content repository.

- **--create-virtualenv**: Create a virtualenv for the environment.
  - Default: `False`

- **--overwrite-virtualenv**: Overwrite existing virtualenvs. Relevant only if the 'create-virtualenv' flag is used.
  - Default: `False`

- **--secret-id**: Secret ID to use for the Google Secret Manager instance. Requires the `DEMISTO_SDK_GCP_PROJECT_ID` environment variable to be set.

- **--instance-name**: Instance name to configure in XSOAR / XSIAM.

- **--run-test-module**: Whether to run test-module on the configured XSOAR / XSIAM instance.
  - Default: `False`

- **--clean**: Clean the repository of temporary files created by the 'lint' command.
  - Default: `False`

- **file_paths**:

- **--console-log-threshold**: Minimum logging threshold for console output. Possible values: DEBUG, INFO, SUCCESS, WARNING, ERROR.

- **--file-log-threshold**: Minimum logging threshold for file output.

- **--log-file-path**: Path to save log files.
### Notes

- The setup-env command downloads integration parameters from Google Secret Manager, if the environment variable DEMISTO_SDK_GCP_PROJECT_ID is set to the GCP project ID.
- The setup-env command creates a virtual environment in the .venv folder if the --create-virtualenv argument is included.
- The setup-env command configures VSCode debugging and linting for the provided file paths or content repository.
- If the --instance-name argument is included, the setup-env command creates an integration instance in your Cortex XSOAR or Cortex XSIAM tenant, with the provided file paths or content repository, if a secret was found in Google Secret Manager.
