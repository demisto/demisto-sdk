## Format

### Overview

This command formats new or modified files to align with the Cortex standard.
This is useful when developing a new integration, script, playbook, incident field, incident type, indicator field, indicator type, layout, or dashboard.
When formatting is complete, the `validate` command runs and notifies you of any issues the formatter could not fix.

### Options
* **-i --input**

    The path of the desired file to be formatted. If no input is specified, the format will be executed on all new/changed files.

* **-o --output**

    Specifies where the formatted file should be saved to. If not used, the default is to overwrite the origin file.

* **-fv --from-version**

    Specifies the minimum version that this content item or content pack is compatible with.

* **-nv ,--no-validate**

   Set when validate on file is not wanted.

* **-ud ,--update-docker**

   Updates the Docker image of the integration/script to the newest available tag.

* **-y/-n, --assume-yes/--assume-no**

  Automatic yes/no to prompts; assume 'yes'/'no' as answer to all prompts and run non-interactively.

* **-d, --deprecate** Deprecates the integration/script/playbook.
* **-g --use-git** Use git to automatically recognize which files changed and run format on them.
* **--prev-ver** Previous branch or SHA1 commit to run checks against.
* **-iu --include-untracked** Whether to include untracked files in the formatting.
* **-at --add-tests** Whether to answer manually to add tests configuration prompt when running interactively.
* **-gr/-ngr -graph/--no-graph** Whether to use the content graph or not.

### Setting fromVersion key in different kind of files:

#### Run without fromVersion flag

**If the source file name already exist in content repo:**

* If fromversion key exists already in current file -> fromversion key will not change.

* If fromversion key does not exist in current file:
    * If fromversion key exist in old file in content repo -> set fromverion key as in old file
    * If fromversion key does not exist in old file -> set fromversion key to default 6.10.0

**If the source file name does not exist in content repo:**

* If fromversion key exists already in current file -> fromversion key will not change.
* If fromversion key does not exist in current file -> is not in file than it will set it to '6.10.0'


#### Run with fromVersion flag

* If fromversion exist already in current file -> will be set to requested fromversion.
* If fromversion does not exist in current file -> add key and set to requested fromversion.

### Examples
```
demisto-sdk format
```
Check your branch changes and runs only on them.
<br/><br/>

```
demisto-sdk format -i Integrations/Pwned-V2/Pwned-V2.yml
```
Goes through the integration file, format it, and override the original file with the necessary changes.
<br/><br/>

```
demisto-sdk format -i Integrations/Pwned-V2/Pwned-V2.yml -o Integrations/Pwned-V2/formatted-Pwned-V2.yml
```
Goes through the integration file, format it, and save it to a new file
(Integrations/Pwned-V2/formatted-Pwned-V2.yml) with the necessary changes, while keeping the origin file as it was.
<br/><br/>

```
demisto-sdk format -i Packs/CortexXDR --from-version 10.10.10
```
Format all JSON/YML files under the Pack CortexXDR.
This also set the fromversion key in all files to '10.10.10'
<br/><br/>

```
demisto-sdk format -i /Users/user/Downloads/Kenna_-_Search_and_Handle_Asset_Vulnerabilities.yml
```
Format the given YML file, however validation will not run as this file is not part of content repository.
<br/><br/>

```
demisto-sdk format -i /Users/user/Downloads/Kenna_-_Search_and_Handle_Asset_Vulnerabilities.yml -o Integrations/Kenna_-_Search_and_Handle_Asset_Vulnerabilities.yml
```
Formats the given YML file and save it in content repository under the specified file path.
Also, validation will run as the output file is in the content repository.
<br/><br/>
