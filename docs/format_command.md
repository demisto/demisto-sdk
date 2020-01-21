## Format

**Format Integration/Script/Playbook YML files according to Demisto's standard.**

### Use Cases
This command is used in order to keep your new or modified YML file with Demisto's standard. This is useful especially
when developing a new integration/script/playbook, and you want to make sure you are keeping up with our standards.
When done formatting, the **validate** command will run, to let you know of things the formatter could not fix.

### Arguments
* **-t {integration, script, playbook}, --type {integration, script, playbook}**

    The type of yml file to be formatted.

* **-s PATH_TO_YML, --source-file PATH_TO_YML**

    The path of the desired yml file to be formatted.

* **-o DESIRED_OUTPUT_PATH, --output_file DESIRED_OUTPUT_PATH**

    The path where the formatted file will be saved to. (Default will be to override origin file)

* **-g, --use-git**

    Formatting changes using git - this will check your branch changes and will run only on them.

### Examples
```
demisto-sdk format -t integration -s Integrations/Pwned-V2/Pwned-V2.yml
```
This will go through the integration file, format it, and override the original file with the necessary changes.
<br/><br/>
```
demisto-sdk format -t integration -s Integrations/Pwned-V2/Pwned-V2.yml -o Integrations/Pwned-V2/formatted-Pwned-V2.yml
```
This will go through the integration file, format it, and save it to a new file
(Integrations/Pwned-V2/formatted-Pwned-V2.yml) with the necessary changes, while keeping the origin file as it was.
<br/><br/>
```
demisto-sdk format -t script -s Scripts/FilterByList/FilterByList.yml
```
This will go through the script file, format it, and override the original file with the necessary changes.
<br/><br/>
```
demisto-sdk format -g
```
this will check your branch changes and will run only on them.
