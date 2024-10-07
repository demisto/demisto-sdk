## Format

**Format Integration/Script/Playbook/IncidentField/IncidentType/IndicatorField/IndicatorType/Layout/Dashboard
        files according to Demisto's standard.**

### Use Cases
This command is used in order to keep your new or modified files with Demisto's standard. This is useful especially
when developing a new Integration/Script/Playbook/IncidentField/IncidentType/IndicatorField/IndicatorType/Layout/Dashboard,
and you want to make sure you are keeping up with our standards.
When done formatting, the **validate** command will run, to let you know of things the formatter could not fix.


### Arguments
* **-i --input**

    The path of the desired file to be formatted. If no input is specified, the format will be executed on all new/changed files.

* **-o --output**

    The file path where the formatted file will be saved to. (Default will be to override origin file).

* **-fv --from-version**

    Specify the fromversion key of the content item.

* **-nv ,--no-validate**

   Set when validate on file is not wanted.

* **-ud ,--update-docker**

   Set if you want to update the docker image of the integration/script to the latest available tag.

* **-v, --verbose**

   Verbose output

* **-y/-n, --assume-yes/--assume-no**

  Automatic yes/no to prompts; assume 'yes'/'no' as answer to all prompts and run non-interactively.

* **-d, --deprecate**

  Set if you want to deprecate the integration/script/playbook
* **-g --use-git** Use git to automatically recognize which files changed and run format on them.
* **--prev-ver** Previous branch or SHA1 commit to run checks against.
* **-iu --include-untracked** Whether to include untracked files in the formatting.
* **-at --add-tests** Whether to answer manually to add tests configuration prompt when running interactively.
* **-gr/-ngr -graph/--no-graph** Whether to use the content graph or not.

### Examples
```
demisto-sdk format
```
This will check your branch changes and will run only on them.
<br/><br/>

```
demisto-sdk format -i Integrations/Pwned-V2/Pwned-V2.yml
```
This will go through the integration file, format it, and override the original file with the necessary changes.
<br/><br/>

```
demisto-sdk format -i Integrations/Pwned-V2/Pwned-V2.yml -o Integrations/Pwned-V2/formatted-Pwned-V2.yml
```
This will go through the integration file, format it, and save it to a new file
(Integrations/Pwned-V2/formatted-Pwned-V2.yml) with the necessary changes, while keeping the origin file as it was.
<br/><br/>

```
demisto-sdk format -i Packs/CortexXDR --from-version 10.10.10
```
This will format all json/yml files under the Pack CortexXDR.
This will also set the fromversion key in all files to '10.10.10'
<br/><br/>

```
demisto-sdk format -i /Users/user/Downloads/Kenna_-_Search_and_Handle_Asset_Vulnerabilities.yml
```
This will format the given yml file, however validation will not ran as this file is not part of content repo.
<br/><br/>

```
demisto-sdk format -i /Users/user/Downloads/Kenna_-_Search_and_Handle_Asset_Vulnerabilities.yml -o Integrations/Kenna_-_Search_and_Handle_Asset_Vulnerabilities.yml
```
This will format the given yml file and save it in content repo under the specified file path.
Also validation will run as the output file is in content repo.
<br/><br/>



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
