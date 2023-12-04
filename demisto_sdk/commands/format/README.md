## Format

**Format Integration/Script/Playbook/IncidentField/IncidentType/IndicatorField/IndicatorType/Layout/Dashboard
        files according to Demisto's standard.**

### Use Cases
This command is used in order to keep your new or modified files with Demisto's standard. This is useful especially
when developing a new Integration/Script/Playbook/IncidentField/IncidentType/IndicatorField/IndicatorType/Layout/Dashboard,
and you want to make sure you are keeping up with our standards.
When done formatting, the **validate** command will run, to let you know of things the formatter could not fix.


### Arguments
* **-i PATH_TO_FILE or PATH_TO_DIRECTORY, --input PATH_TO_FILE or PATH_TO_DIRECTORY**
The path of the content pack/file to validate specifically.
* **-g, --use-git**, 
Use git to automatically recognize which files changed and run format on them.
* **--prev-ver**
Previous branch or SHA1 commit to run checks against.
* **--category-to-run**
Run specific validations by stating category they're listed under in the config file.
* **--config-path**
Path for a config file to run, if not given - will run the default path at: demisto_sdk/commands/validate/default_config.toml .
* **--skip-old-format**
Wether to skip the old format flow.
* **--run-new-format**
Wether to run the new format flow.
* **-j, --json-file**
The JSON file path to which to output the command results.

### Examples
```
demisto-sdk format
```
This will check your branch changes and will run only on them.


```
demisto-sdk format -i Integrations/Pwned-V2/Pwned-V2.yml
```
This will go through the integration file, format it, and override the original file with the necessary changes.
