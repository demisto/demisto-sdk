## prepare-content

### Overview

This command prepares content to upload to the platform. If the content item is a pack, prepare-content creates the pack zip file. If the content item is an integration/script/rule, prepare-content creates the unified YAML file.

NOTE: The prepare-content command replaces the unify command.
### Options

- **--input**: Comma-separated list of paths to directories or files to unify.

- **--all**: Run prepare-content on all content packs. If no output path is given, will dump the result in the current working path.
  - Default: `False`

- **--graph**: Whether to use the content graph
  - Default: `False`

- **--skip-update**: Whether to skip updating the content graph (used only when graph is true)
  - Default: `False`

- **--output**: The output dir to write the unified YML to

- **--custom**: Add test label to unified YML id/name/display

- **--force**: Forcefully overwrites the preexisting YML if one exists
  - Default: `False`

- **--ignore-native-image**: Whether to ignore the addition of the native image key to the YML of a script/integration
  - Default: `False`

- **--marketplace**: The marketplace the content items are created for, that determines usage of marketplace unique text.
  - Default: `xsoar`

- **--console-log-threshold**: Minimum logging threshold for console output. Possible values: DEBUG, INFO, SUCCESS, WARNING, ERROR.

- **--file-log-threshold**: Minimum logging threshold for file output.

- **--log-file-path**: Path to save log files.

- **--private-packs-path**: Path to pack folder in private packs repo (optional).
### Examples

`demisto-sdk prepare-content -i Integrations/MyInt -o Integrations`
Takes the integration components in Integrations/MyInt directory and unifies them to a single YAML file that is created
in the Integrations directory.

`demisto-sdk prepare-content -i Scripts/MyScr -o Scripts`
Takes the script components in Scripts/MyScr directory and unifies them to a single YAML
file that is created in the Scripts directory.

`demisto-sdk prepare-content -u Integrations/MyInt -c Test`
Appends to the unified YAML name/script/id a label - Test that prevents bumps
with the uploaded unified YAML and the original integration/script on the server.
origin yml: {name: integration} --> unified yml: {name: integration - Test}

`demisto-sdk prepare-content -i Packs/RBVM/GenericModules/genericmodule-RBVM.json`
Takes the GenericModule input file genericmodule-RBVM.json, unifies it with its dashboards
and saves the unified file in the same directory as the input file Packs/RBVM/GenericModules.
<br/><br/>

`demisto-sdk prepare-content -i Packs/RBVM/GenericModules/genericmodule-RBVM.json -o Packs/RBVM/`
Takes the GenericModule input file genericmodule-RBVM.json, unifies it with its dashboards and
saves the unified file in the given output directory Packs/RBVM.

`demisto-sdk prepare-content -i Packs/SIEMPack/ParsingRule/MyParsingRule -o Packs/SIEMPack/ParsingRule`
Takes the parsing rules components (YAML, XIF and JSON) from the ParsingRule/MyParsingRule directory
and unifies them into a single YAML file that is created in the ParsingRules directory.
