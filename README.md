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

### [Unify](https://github.com/demisto/demisto-sdk/tree/master/docs/unify_command.md)

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

### [Split-yml](https://github.com/demisto/demisto-sdk/tree/master/docs/split_yml_command.md)

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

### [Validate](https://github.com/demisto/demisto-sdk/tree/master/docs/validate_command.md)

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
<br>
`demisto-sdk validate -p Integrations/Pwned-V2/Pwned-V2.yml`
This will validate the file Integrations/Pwned-V2/Pwned-V2.yml only.

### [Lint](https://github.com/demisto/demisto-sdk/tree/master/docs/lint_command.md)

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

### [Secrets](https://github.com/demisto/demisto-sdk/tree/master/docs/secrets.md)

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

### Create

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

### [Format](https://github.com/demisto/demisto-sdk/tree/master/docs/format_command.md)

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

### [Run-playbook](https://github.com/demisto/demisto-sdk/tree/master/docs/run_playbook_command.md)

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


### [Upload](https://github.com/demisto/demisto-sdk/tree/master/docs/upload_command.md)

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


### [Run](https://github.com/demisto/demisto-sdk/tree/master/docs/run_command.md)

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


## [init](https://github.com/demisto/demisto-sdk/tree/master/docs/init_command.md)
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
