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

### Autocomplete
Our CLI supports autocomplete for Linux/MacOS machines, you can turn this feature on by running one of the following:
for zsh users run in the terminal
```
eval "$(_DEMISTO_SDK_COMPLETE=source_zsh demisto-sdk)"
```
for regular bashrc users run in the terminal
```
eval "$(_DEMISTO_SDK_COMPLETE=source demisto-sdk)"
```

## Commands

### [Unify](demisto_sdk/commands/unify/unify_command.md)

Unify the code, image and description files to a single Demisto yaml file.
**Arguments**:
* **-i INDIR, --indir INDIR**
  The path to the directory in which the files reside
* **-o OUTDIR, --outdir OUTDIR**
  The path to the directory into which to write the unified yml file

**Example**:
`demisto-sdk unify -i Integrations/MyInt -o Integrations`
This will grab the integration components in "Integrations/MyInt" directory and unify them to a single yaml file
that will be created in the "Integrations" directory.

### [Split-yml](demisto_sdk/commands/split_yml/split_yml_command.md)

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
`demisto-sdk split-yml -i Integrations/integration-MyInt.yml -o Integrations/MyInt -m`
This will split the yml file to a directory with the integration components (code, image, description, pipfile etc.)

### [Validate](demisto_sdk/commands/validate/validate_command.md)

Makes sure your content repository files are in order and have valid yml file scheme.

**Arguments**:
* **--no-backward-comp**
                        Whether to check backward compatibility or not.
* **-j, --conf-json**
                        Validate the conf.json file.
* **-i, --id-set**
                        Create the id_set.json file.
* **--prev-ver**
                        Previous branch or SHA1 commit to run checks against.
* **-g, --use-git**
                        Validate changes using git - this will check your branch changes and will run only on them.
* **--post-commit** Whether the validation is done after you committed your files,
                    this will help the command to determine which files it should check in its
                    run. Before you commit the files it should not be used. Mostly for build validations.
* **-p, --path**
                        Path of file to validate specifically.

**Examples**:
`demisto-sdk validate`
This will validate all the files in content repo.

`demisto-sdk validate -p Integrations/Pwned-V2/Pwned-V2.yml`
This will validate the file Integrations/Pwned-V2/Pwned-V2.yml only.

### [Lint](demisto_sdk/commands/lint/lint_command.md)

Run lintings (flake8, mypy, pylint, bandit) and pytest.
pylint and pytest will run within all the docker images of an integration/script. Meant to be used with integrations/scripts that use the folder (package) structure. Will lookup up what docker image to use and will setup the dev dependencies and file in the target folder.
**Arguments**:
* **-d DIR, --dir DIR**
  Specify directory of integration/script. Also supports several direcories as a CSV (default: None)
* **--no-pylint**
  Do NOT run pylint linter (default: False)
* **--no-mypy**
  Do NOT run mypy static type checking (default: False)
* **--no-flake8**
  Do NOT run flake8 linter (default: False)
* **--no-bandit**
  Do NOT run bandit linter (default: False)
* **--no-test**
  Do NOT test (skip pytest) (default: False)
* **-r, --root**
  Run pytest container with root user (default: False)
* **-p, --parallel**
  Run tests in parallel (default: False)
* **-m, --max-workers**
  The max workers to use in a parallel run (default: 10)
* **-g, --git**
  Run only on packages that changes between the current branch and content repo's origin/master branch (default: False)
* **-a, --run-all-tests**
  Run lint on all directories in content repo (default: False)
* **-k, --keep-container**
  Keep the test container (default: False)
* **-v, --verbose**
  Verbose output (default: False)
* **--outfile** Specify a file path to save failing package list. (default: None)
* **--cpu-num CPU_NUM**
  Number of CPUs to run pytest on (can set to `auto` for automatic detection of the number of CPUs.) (default: 0)

**Example**:
`demisto-sdk lint -d Integrations/PaloAltoNetworks_XDR,Scripts/HellowWorldScript --no-mypy -p -m 2`
This will parallel run the linters, excluding mypy, on the python files inside the "Integrations/PaloAltoNetworks_XDR" and "Scripts/HelloWorldScript" directories, using 2 workers (threads).

### [Secrets](demisto_sdk/commands/secrets/secrets.md)

Run Secrets validator to catch sensitive data before exposing your code to public repository. Attach full path to whitelist to allow manual whitelists. Default file path to secrets is "./Tests/secrets_white_list.json".
**Arguments**:
* **--post-commit**
   Whether the secretes validation is done after you committed your files.
   This will help the command to determine which files it should check in its
   run. Before you commit the files it should not be used. Mostly for build
   validations. (default: False)

* **-wl WHITELIST, --whitelist WHITELIST**
    Full path to whitelist file, file name should be "secrets_white_list.json" (default: ./Tests/secrets_white_list.json)

* **-ie, --ignore-entropy**
    Ignore entropy algorithm that finds secret strings (passwords/api keys)

**Examples**:
`demisto-sdk secrets`
This will run the secrets validator on your files.

### [Create](demisto_sdk/commands/create_artifacts/create_command.md)

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

### [Format](demisto_sdk/commands/format/format_command.md)

Format your integration/script/playbook yml file according to Demisto's standard automatically.
**Arguments**:
* *-t {integration, script, playbook}, --type {integration, script, playbook}*
                        The type of yml file to be formatted.
* *-s PATH_TO_YML, --source-file PATH_TO_YML*
                        The path of the desired yml file to be formatted.
* *-o DESIRED_OUTPUT_PATH, --output_file DESIRED_OUTPUT_PATH*
                        The path where the formatted file will be saved to. (Default will be to override origin file)

**Examples**:
` demisto-sdk format -t integration -s Integrations/Pwned-V2/Pwned-V2.yml`.
This will go through the integration file, format it, and override the original file with the necessary changes.

### [Run-playbook](demisto_sdk/commands/run_playbook/run_playbook_command.md)

Run a playbook in a given Demisto instance.
DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
You can either specify a URL as an environment variable named: DEMISTO_BASE_URL, or enter it as an argument.

**Arguments**:
* **-u, --url**
                        URL to a Demisto instance.
* **-p, --playbook_id**
                        The ID of the playbook to run.
* **-w, --wait**
                        Wait until the playbook run is finished and get a response.
                        (default: True)
* **-t, --timeout**
                        Timeout for the command. The playbook will continue to run in Demisto.
                        (default: 90)

**Examples**:
`DEMISTO_API_KEY=<API KEY> demisto-sdk run-playbook -p 'playbook_name' -u 'https://demisto.local'.`
This will run the playbook `playbook_name` in Demisto instance `https://demisto.local` and will wait for the playbook to finish its run.


### [Upload](demisto_sdk/commands/upload/upload_command.md)

Upload an integration to Demisto instance.

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Demisto base URL, and `DEMISTO_API_KEY` environment variable should contain a valid Demisto API Key.

**Arguments**:
* **-i INTEGRATION_PATH, --inpath INTEGRATION_PATH**

    The path of an integration file or a package directory to upload

* **-k, --insecure**

    Skip certificate validation

* **-v, --verbose**

    Verbose output


**Example**:

```
demisto-sdk upload -i Integrations/GoogleCloudTranslate/integration-GoogleCloudTranslate.yml
```
This will upload the integration YML file `integration-GoogleCloudTranslate.yml` to the Demisto instance.


### [Run](demisto_sdk/commands/run_cmd/run_command.md)

Run an integration command in the playground of a remote Demisto instance and retrieves the output.

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Demisto base URL, and `DEMISTO_API_KEY` environment variable should contain a valid Demisto API Key.

**Arguments**:
* **-q QUERY, --query QUERY**

    The query to run

* **-k, --insecure**

    Skip certificate validation

* **-v, --verbose**

    Verbose output

* **-D, --debug**

    Whether to enable the debug-mode feature or not, if you want to save the output file, please use the --debug-path option

* **--debug-path [DEBUG_LOG]**

    The path to save the debug file at, if not specified the debug file will be printed to the terminal


**Example**:
```
demisto-sdk run -q '!gct-translate-text text="ciao" target="iw"'
```
This will run the query `!gct-translate-text text="ciao" target="iw"` on the playground of the Demisto instance and print the output.


### Generate Test Playbook

Generate Test Playbook from integration/script yml
**Arguments**:
* *-i, --infile*
   Specify integration/script yml path (must be a valid yml file)
* *-o, --outdir*
   Specify output directory (Default: current directory)
* *-n, --name*
   Specify test playbook name
* *-t, --type{integration,script}*
   YAML type (default: integration)

**Examples**:
`demisto-sdk generate-test-playbook -i Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml -n TestXDRPlaybook -t integration -o TestPlaybooks`
This will create a test playbook in TestPlaybook folder, with filename `TestXDRPlaybook.yml`.


## [init](demisto_sdk/commands/init/init_command.md)
Create a pack, integration or script template. If `--integration` and `--script` flags are not given the command will create a pack.

**Arguments**:
* **-n, --name** The name given to the files and directories of new pack/integration/script being created
* **--id** The id used for the yml file of the integration/script
* **-o, --outdir** The directory to which the created object will be saved
* **--integration** Create an integration.
* **--script** Create a script.
* **--pack** Create a pack.

**Example**:
`demisto-sdk init --integration -n MyNewIntegration -o path/to/my/dir`
This will create a new integration template named MyNewIntegration within "path/to/my/dir" directory.


### Convert JSON to Demisto Outputs

**Arguments**:
* *-c, --command*
    Command name (e.g. xdr-get-incidents)
* *-i, --infile*
    Valid JSON file path. If not specified then script will wait for user input in the terminal
* *-p, --prefix*
    Output prefix like Jira.Ticket, VirusTotal.IP
* *-o, --outfile*
    Output file path, if not specified then will print to stdout
* *-v, --verbose*
    Verbose output - mainly for debugging purposes
* *-int, --interactive*
    If passed, then for each output field will ask user interactively to enter the description. By default is interactive mode is disabled

**Examples**:
<br/>`demisto-sdk json-to-outputs -c jira-get-ticket -p Jira.Ticket -i path/to/valid.json`
<br/>if valid.json looks like
```json
{
    "id": 100,
    "title": "do something title",
    "created_at": "2019-01-01T00:00:00"
}
```
This command will print to the stdout the following:
```yaml
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
```



## In the code
You can import the SDK core class in your python code as follows:

`from demisto_sdk.__main__ import DemistoSDK`

## Contributions
For information regarding contributing, press [here](resources/contribution/CONTRIBUTION.md)
