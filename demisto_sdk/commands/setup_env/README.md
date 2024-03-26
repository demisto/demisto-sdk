# Setup Environment

The Command sets up a content environment and an integration/script environment. The command will configure VSCode and XSOAR/XSIAM instances for development and testing.

**Notes**

* This command will download integration parameters from Google Secret Manager, if the enviornment variable **DEMISTO_SDK_GCP_PROJECT_ID** is set to the GCP project ID.
* It will also create a virtual environment in the .venv folder if **--create-virtualenv** is passed.
* It will configure VSCode debugging and linting for the provided file paths or content repo.
* It will create a XSOAR/XSIAM instance and configure it for testing with the provided file paths or content repo, if a secret was found in Google Secret Manager.

## Usage

```
demisto-sdk setup-env [OPTIONS] [FILE_PATHS]
```

## Options

- **-i, --input**
Paths to content integrations or script to setup the environment. If not provided, will configure the environment for the content repository

- **--create-virtualenv**
Create a virtualenv for the environment.

- **--overwrite-virtualenv**
Overwrite existing virtualenvs. Use with the create-virtualenv flag.

- **-secret-id**
Secret ID, to use with Google Secret Manager instance. If not provided, will use the integration id.
- **--instance-name**
Instance name to configure in XSOAR/XSIAM.
- **--run-test-module**
Whether to run the test-module of the integration.
- **--clean**
Clean the repo out of the temp `CommonServerPython.py` files, `demistomock.py` and other files that were created by `lint`.
