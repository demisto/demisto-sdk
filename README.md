[![PyPI version](https://badge.fury.io/py/demisto-sdk.svg)](https://badge.fury.io/py/demisto-sdk)
[![CircleCI](https://circleci.com/gh/demisto/demisto-sdk/tree/master.svg?style=svg)](https://circleci.com/gh/demisto/demisto-sdk/tree/master)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/ppwwyyxx/OpenPano.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/demisto/demisto-sdk/context:python)


# Demisto SDK

The Demisto SDK library can be used to manage your Demisto content with ease and efficiency.
The library uses python 3.7+.

## Usage

### Installation

1. **Install** - `pip3 install demisto-sdk`

2. **Upgrade** - `pip3 install --upgrade demisto-sdk`

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

For detailed command usage press [here](demisto_sdk/commands/init/init_command.md)

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

For detailed command usage press [here](demisto_sdk/commands/validate/validate_command.md)

---

### Lint

Run lintings (flake8, mypy, pylint, bandit) and pytest.
pylint and pytest will run within all the docker images of an integration/script. Meant to be used with integrations/scripts that use the folder (package) structure. Will lookup up what docker image to use and will setup the dev dependencies and file in the target folder.

**Examples**:

1. This command will parallel run the linters, excluding mypy, on the python files inside the "Integrations/PaloAltoNetworks_XDR" and "Scripts/HelloWorldScript" directories, using 2 workers (threads):

   ```shell
   demisto-sdk lint -d Integrations/PaloAltoNetworks_XDR,Scripts/HellowWorldScript --no-mypy -p -m 2
   ```

For detailed command usage press [here](demisto_sdk/commands/lint/lint_command.md)

---

### Secrets

Run Secrets validator to catch sensitive data before exposing your code to public repository. Attach full path to whitelist to allow manual whitelists. Default file path to secrets is "./Tests/secrets_white_list.json".

**Examples**:

1. This will run the secrets validator on your files:

   ```shell
   demisto-sdk secrets
   ```

For detailed command usage press [here](demisto_sdk/commands/secrets/secrets_command.md)

---

### Unify

Unify the code, image and description files to a single Demisto yaml file.

**Examples**:

1. This command will grab the integration components in `Integrations/MyInt` directory and unify them to a single yaml file
   that will be created in the "Integrations" directory.

   ```shell
   demisto-sdk unify -i Integrations/MyInt -o Integrations
   ```

For detailed command usage press [here](demisto_sdk/commands/unify/unify_command.md)

---

### Split-yml

Extract code, image and description files from a demisto integration or script yml file.

**Examples**

1. This command will split the yml file to a directory with the integration components (code, image, description, pipfile etc.

   ```shell
   demisto-sdk split-yml -i Integrations/integration-MyInt.yml -o Integrations/MyInt
   ```

2. This command will split the yml file to a directory with the script components (code, description, pipfile etc.)

   ```shell
   demisto-sdk split-yml -i Scripts/script-MyInt.yml -o Scripts/MyInt
   ```

For detailed command usage press [here](demisto_sdk/commands/split_yml/split_yml_command.md)

---

### Create

Create content artifacts.

**Examples**:

1. This command will create content artifacts in the current directory:

   ```shell
   demisto-sdk create -a .
   ```

For detailed command usage press [here](demisto_sdk/commands/create_artifacts/create_command.md)

---

### Format

Format your integration/script/playbook yml file according to Demisto's standard automatically.

**Examples**:

1. This command will go through the integration file, format it, and override the original file with the necessary changes:

   ```shell
   demisto-sdk format -t integration -s Integrations/Pwned-V2/Pwned-V2.yml
   ```

For detailed command usage press [here](demisto_sdk/commands/format/format_command.md)

---

### Run

Run an integration command in the playground of a remote Demisto instance and retrieves the output.

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Demisto base URL, and `DEMISTO_API_KEY` environment variable should contain a valid Demisto API Key.

**Examples**:

1. This command will run the query `!gct-translate-text text="ciao" target="iw"` on the playground of the Demisto instance and print the output:

   ```shell
   demisto-sdk run -q '!gct-translate-text text="ciao" target="iw"
   ```

For detailed command usage press [here](demisto_sdk/commands/run_cmd/run_command.md)

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

For detailed command usage press [here](demisto_sdk/commands/run_playbook/run_playbook_command.md)

---

### Upload

Upload an integration to Demisto instance.

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Demisto base URL, and `DEMISTO_API_KEY` environment variable should contain a valid Demisto API Key.

**Examples**:

1. This will upload the integration YML file `integration-GoogleCloudTranslate.yml` to the Demisto instance:

   ```shell
   demisto-sdk upload -i Integrations/GoogleCloudTranslate/integration-GoogleCloudTranslate.yml

---

## generate-docs
Generate documentation file for integration, playbook or script from yaml file.

**Arguments**:
* **-i, --input**
    Path of the yml file.

* **-o, --output**
    The output dir to write the documentation file into, documentation file name is README.md.

* **-t, --file_type**
    The type of yml file. When the argument is empty, the type will be selected automatically.

* **-e, --examples**
    In order to create example, DEMISTO_BASE_URL environment variable should contain the Demisto base URL, and DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    **For integration** - Path for file containing command or script examples.
    Each Command should be in a separate line. **For script** - the script example surrounded by double quotes.
    When the argument is empty, the documentation will be generate without examples.

* **-id, --id_set**
    Path of updated id_set.json file, used for generates script documentation.
     When the argument is empty, the documentation will be generate without `Used In` section.

* **-v, --verbose**
    Verbose output - mainly for debugging purposes.

**Examples**:
`demisto-sdk generate-docs -o /Users/Documentations -i /demisto/content/Playbooks/playbook-Block_IP_-_Generic.yml`
This will generate documentation file to Block IP - Generic playbook in /Users/Documentations/README.md.

`demisto-sdk generate-docs -o /Users/Documentations -i /demisto/content/Integrations/Tanium_v2/Tanium_v2.yml -c /Users/tanium_commands.txt`
This will generate documentation file to Tanium V2 integration in /Users/Documentations/README.md, the file /Users/tanium_commands.txt should contains the example commands to execute.

`demisto-sdk generate-docs -o /Users/Documentations -i /demisto/content/Scripts/script-PrintErrorEntry.yml -id /demisto/content/Tests/id_set.json -e "!PrintErrorEntry message=Hi"`
This will generate documentation file to PrintErrorEntry script in /Users/Documentations/README.md. id_set.json should be updated to gets all the integration that uses this script.

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
    pip3 install tox
    ```
    Then setup dev virtual envs for python 3 (will also install all necessary requirements):
    ```
    tox
    ```
5) Set your IDE to use the virtual environment you created using the following path:
`/{path_to_demisto-sdk}/demisto-sdk/.tox/py37/bin/python`

---

### Generate-test-playbook

Generate Test Playbook from integration/script yml

**Examples**:

1. This command will create a test playbook in TestPlaybook folder, with filename `TestXDRPlaybook.yml`:

   ```shell
   demisto-sdk generate-test-playbook -i Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml -n TestXDRPlaybook -t integration -o TestPlaybooks`
   ```

For detailed command usage press [here](demisto_sdk/commands/generate_test_playbook/generate_test_playbook_command.md)

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

For detailed command usage press [here](demisto_sdk/commands/json_to_outputs/json_to_outputs_command.md)

---

### How to run commands in your development environment
In the Demisto-SDK repository while on the git branch you want to activate and run this command to use python 3.7:
 ```
 source .tox/py37/bin/activate
 ```
or this command to use python 3.8:

For detailed command usage press [here](demisto_sdk/commands/upload/upload_command.md)

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
For information regarding contributing, press [here](CONTRIBUTION.md).
For release guide, press [here](docs/release_guide.md)
