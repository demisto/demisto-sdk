[![PyPI version](https://badge.fury.io/py/demisto-sdk.svg)](https://badge.fury.io/py/demisto-sdk)
[![CircleCI](https://circleci.com/gh/demisto/demisto-sdk/tree/master.svg?style=svg)](https://circleci.com/gh/demisto/demisto-sdk/tree/master)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/ppwwyyxx/OpenPano.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/demisto/demisto-sdk/context:python)


# Demisto SDK

The Demisto SDK library can be used to manage your Demisto content with ease and efficiency.
The library uses python 3.7+.

## Usage

### Installation

1. **Install** - `pip install demisto-sdk`

2. **Upgrade** - `pip install --upgrade demisto-sdk`

3. **Demisto server demisto-sdk integration** - In order that demisto-sdk and Demisto server communicate, perfrom the following steps:

   1. Get an API key for Demisto-server - `Settings` -> ` Integrations` -> `API keys` -> `Get your Key` (copy it, you will be to copy it once)
   2. Add the following parameters to `~/.zshrc` and `~/.bash_profile`:

   ```shell
   export DEMISTO_BASE_URL=<http or https>://<demisto-server url or ip>:<port>
   export DEMISTO_API_KEY=<API key>
   ```

   for example:

   ```shell
   export DEMISTO_BASE_URL=http://127.0.0.1:8080
   export DEMISTO_API_KEY=XXXXXXXXXXXXXXXXXXXXXX
   ```

   3. Reload your terminal before continue.

---

### CLI usage

You can use the SDK in the CLI as follows:

```shell
demisto-sdk <command> <args>
```

For more information, run `demisto-sdk -h`.
For more information on a specific command execute `demisto-sdk <command> -h`.

----

## Commands

Supported commands:

1. [init](#Init)
2. [Validate](#validate)
3. [Lint](#lint)
4. [Secrets](#secrets)
5. [Unify](#unify)
6. [Split-yml](#split-yml)
7. [Create](#create)
8. [Format](#format)
9. [Run](#run)
10. [Run-playbook](#run-playbook)
11. [Upload](#upload)
12. [Generate-test-playbook](#generate-test-playbook)
13. [Json-to-outputs](#json-to-outputs)

---

### Init

Create a pack, integration or script template. If `--integration` and `--script` flags are not given the command will create a pack.

**Examples**:

1. This command will create a new integration template named MyNewIntegration within "path/to/my/dir" directory:

   ```shell
   demisto-sdk init --integration -n MyNewIntegration -o path/to/my/dir
   ```

For detalied command usage press [here](demisto_sdk/commands/init/init_command.md)

---

### Validate

Makes sure your content repository files are in order and have valid yml file scheme.

**Examples**:

1. This command will validate all the files in content repo:

   ```shell
   demisto-sdk validate
   ```

2. This will validate the file Integrations/Pwned-V2/Pwned-V2.yml only:

   ```shell
   demisto-sdk validate -p Integrations/Pwned-V2/Pwned-V2.yml
   ```

For detalied command usage press [here](demisto_sdk/commands/validate/validate_command.md)

---

### Lint

Run lintings (flake8, mypy, pylint, bandit) and pytest.
pylint and pytest will run within all the docker images of an integration/script. Meant to be used with integrations/scripts that use the folder (package) structure. Will lookup up what docker image to use and will setup the dev dependencies and file in the target folder.

**Examples**:

1. This command will parallel run the linters, excluding mypy, on the python files inside the "Integrations/PaloAltoNetworks_XDR" and "Scripts/HelloWorldScript" directories, using 2 workers (threads):

   ```shell
   demisto-sdk lint -d Integrations/PaloAltoNetworks_XDR,Scripts/HellowWorldScript --no-mypy -p -m 2
   ```

For detalied command usage press [here](demisto_sdk/commands/lint/lint_command.md)

---

### Secrets

Run Secrets validator to catch sensitive data before exposing your code to public repository. Attach full path to whitelist to allow manual whitelists. Default file path to secrets is "./Tests/secrets_white_list.json".

**Examples**:

1. This will run the secrets validator on your files:

   ```shell
   demisto-sdk secrets
   ```

For detalied command usage press [here](demisto_sdk/commands/secrets/secrets.md)

---

### Unify

Unify the code, image and description files to a single Demisto yaml file.

**Examples**:

1. This command will grab the integration components in `Integrations/MyInt` directory and unify them to a single yaml file
   that will be created in the "Integrations" directory.

   ```shell
   demisto-sdk unify -i Integrations/MyInt -o Integrations
   ```

For detalied command usage press [here](demisto_sdk/commands/unify/unify_command.md)

---

### Split-yml

Extract code, image and description files from a demisto integration or script yml file.

**Examples**

1. This command will split the yml file to a directory with the integration components (code, image, description, pipfile etc.

   ```shell
   demisto-sdk split-yml -i Integrations/integration-MyInt.yml -o Integrations/MyInt -m
   ```

2. This command will split the yml file to a directory with the script components (code, description, pipfile etc.)

   ```shell
   demisto-sdk split-yml -i Scripts/script-MyInt.yml -o Scripts/MyInt -m
   ```

For detalied command usage press [here](demisto_sdk/commands/split_yml/split_yml_command.md)

---

### Create

Create content artifacts.

**Examples**:

1. This command will create content artifacts in the current directory:

   ```shell
   demisto-sdk create -a .
   ```

For detalied command usage press [here](demisto_sdk/commands/create_artifacts/create_command.md)

---

### Format

Format your integration/script/playbook yml file according to Demisto's standard automatically.

**Examples**:

1. This command will go through the integration file, format it, and override the original file with the necessary changes:

   ```shell
   demisto-sdk format -t integration -s Integrations/Pwned-V2/Pwned-V2.yml
   ```

For detalied command usage press [here](demisto_sdk/commands/format/format_command.md)

---

### Run

Run an integration command in the playground of a remote Demisto instance and retrieves the output.

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Demisto base URL, and `DEMISTO_API_KEY` environment variable should contain a valid Demisto API Key.

**Examples**:

1. This command will run the query `!gct-translate-text text="ciao" target="iw"` on the playground of the Demisto instance and print the output:

   ```shell
   demisto-sdk run -q '!gct-translate-text text="ciao" target="iw"
   ```

For detalied command usage press [here](demisto_sdk/commands/run_cmd/run_command.md)

---

### Run-playbook

Run a playbook in a given Demisto instance.
DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
You can either specify a URL as an environment variable named: DEMISTO_BASE_URL, or enter it as an argument.

**Examples**:

1. This command will run the playbook `playbook_name` in Demisto instance `https://demisto.local` and will wait for the playbook to finish its run:

   ```shell
   DEMISTO_API_KEY=<API KEY> demisto-sdk run-playbook -p 'playbook_name' -u 'https://demisto.local'
   ```

For detalied command usage press [here](demisto_sdk/commands/run_playbook/run_playbook_command.md)

---

### Upload

Upload an integration to Demisto instance.

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Demisto base URL, and `DEMISTO_API_KEY` environment variable should contain a valid Demisto API Key.

**Examples**:

1. This will upload the integration YML file `integration-GoogleCloudTranslate.yml` to the Demisto instance:

   ```shell
   demisto-sdk upload -i Integrations/GoogleCloudTranslate/integration-GoogleCloudTranslate.yml
   ```

For detalied command usage press [here](demisto_sdk/commands/upload/upload_command.md)

---

### Generate-test-playbook

Generate Test Playbook from integration/script yml

**Examples**:

1. This command will create a test playbook in TestPlaybook folder, with filename `TestXDRPlaybook.yml`:

   ```shell
   demisto-sdk generate-test-playbook -i Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml -n TestXDRPlaybook -t integration -o TestPlaybooks`
   ```

For detalied command usage press [here](demisto_sdk/commands/generate_test_playbook/generate_test_playbook_command.md)

---


### Convert JSON to Demisto Outputs
Convert JSON format to demisto entry context yaml format.

**Examples**:

1. The following command :

   ```
   demisto-sdk json-to-outputs -c jira-get-ticket -p Jira.Ticket -i path/to/valid.json
   ```

   if valid.json looks like

   ```json
   {
       "id": 100,
       "title": "do something title",
       "created_at": "2019-01-01T00:00:00"
   }
   ```

   This command will print to the stdout the following:

   ````yaml
   arguments: []
   name: jira-get-ticket
   outputs:
   - contextPath: Jira.Ticket.id
     description: ''
     type: Number
   - contextPath: Jira.Ticket.title
     description: ''
     type: String
   - contextPath: Jira.Ticket.created_at
     description: ''
     type: Date
   ````

For detalied command usage press [here](demisto_sdk/commands/json_to_outputs/json_to_outputs_command.md)

---

### Autocomplete

Our CLI supports autocomplete for Linux/MacOS machines, you can turn this feature on by running one of the following:
for zsh users run in the terminal

```shell
eval "$(_DEMISTO_SDK_COMPLETE=source_zsh demisto-sdk)"
```

for regular bashrc users run in the terminal

```shell
eval "$(_DEMISTO_SDK_COMPLETE=source demisto-sdk)"
```

---

## License
MIT - See [LICENSE](LICENSE) for more information.

---

## Contributions
Contributions are welcome and appreciated.\
For information regarding contributing, press [here](resources/contribution/CONTRIBUTION.md).
