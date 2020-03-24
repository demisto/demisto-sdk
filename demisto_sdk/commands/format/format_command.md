## Format

**Format Integration/Script/Playbook/IncidentField/IncidentType/IndicatorField/IndicatorType/Layout/Dashboard
        files according to Demisto's standard.**

### Use Cases
This command is used in order to keep your new or modified YML file with Demisto's standard. This is useful especially
when developing a new integration/script/playbook, and you want to make sure you are keeping up with our standards.
When done formatting, the **validate** command will run, to let you know of things the formatter could not fix.

### Arguments
* **-i PATH_TO_FILE or PATH_TO_DIRECTORY, --input PATH_TO_FILE or PATH_TO_DIRECTORY**

    The path of the desired file to be formatted.

* **-o DESIRED_OUTPUT_PATH, --output DESIRED_OUTPUT_PATH**

    The path where the formatted file will be saved to. (Default will be to override origin file)

### Examples
```
demisto-sdk format
```
this will check your branch changes and will run only on them.
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
demisto-sdk format -i Packs/CortexXDR
```
this will format all json/yml files under the Pack CortexXDR.

```
demisto-sdk format -i /Users/user/Downloads/Kenna_-_Search_and_Handle_Asset_Vulnerabilities.yml
```
this will format the given yml file, however validation will not ran as this file is not part of content repo.

```
demisto-sdk format -i /Users/user/Downloads/Kenna_-_Search_and_Handle_Asset_Vulnerabilities.yml -o Integrations/Kenna_-_Search_and_Handle_Asset_Vulnerabilities.yml
```
this will format the given yml file and save it in content repo under the specified directory.

```
demisto-sdk format -i Packs/CortexXDR -fv 9.9.9
```
this will format all yml/json files under Pack CortexXDR and change fromversion key in all to '9.9.9'

```
demisto-sdk format -i Integrations/Pwned-V2/Pwned-V2.yml -fv 9.9.9
```
This will go through the integration file, format it:
if the file had fromversion key before than it will be overwrited to '9.9.9'
if the file did not have fromversion key before than it will be added and set to '9.9.9'

```
demisto-sdk format -i Integrations/Pwned-V2/Pwned-V2.yml -o Integrations/Pwned-V2/Pwned-V2-formatted-file.yml -fv 9.9.9
```
This will go through the integration file, format it:
if the specified output path already exists in content repo than:
the output file in content had fromversion key before than it will be overwrited to '9.9.9'
if the file did not have fromversion key before than it will be added and set to '9.9.9'

```
demisto-sdk format
```
this will go through all
if the file is a old file which means that it is only modified by your branch:
    if YAML file:
        if fromversion key in file than it will not change.
        if fromversion key is not in file than it will set it to '1.0.0'
    if JSON file:
        if fromversion key in file than it will not change.
        if fromversion key is not in file than it will set it to '5.0.0'
if the file is not an old file, which means that it is added by you branch:
    if fromversion key in file than it will not change.
    if fromversion key is not in file than it will set it to '5.0.0'
