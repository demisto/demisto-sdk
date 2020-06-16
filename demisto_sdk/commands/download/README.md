## Download

**Download & merge custom content from Demisto instance to local content repository.**

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Demisto base URL, and `DEMISTO_API_KEY` environment variable should contain a valid Demisto API Key.
To set the environment variables, run the following shell commands:
```
export DEMISTO_BASE_URL=<YOUR_DESMISTO_BASE_URL>
export DEMISTO_API_KEY=<YOUR_DEMISTO_API_KEY>
```


### Use Cases
This command is used in order to download & merge custom content from Demisto instance to local content repository. This is useful when developing custom content in Demisto instance and then
downloading it to the local content repository in order to make a contribution.


### Behavior
The download is one-directional, data goes from the server to the repo.

If there are files that exist both in the output directory and are specified in the input, they will be ignored. To override this behavior such that existing files will be merged with their newer version, use the force flag.

### Arguments
* **-o PACK_PATH, --output PACK_PATH**

    The path of a package directory to download custom content to.

* **-i "file_name_1" ... -i "file_name_n", --input "file_name_1" ... --input "file_name_n"**

    Custom content file name to be downloaded. Can be provided multiple times. File names can be retrieved using the -lf flag.

* **-lf, --list-files**

    Prints a list of all custom content files available to be downloaded.

* **-a, --all-custom-content**

    Download all available custom content files.

* **-fmt, --run-format**

    Whether to run demisto-sdk format on downloaded files or not.

* **-f, --force**

    Whether to override existing files or not.

* **--insecure**

    Skip certificate validation.

* **-v, --verbose**

    Verbose output.


### Asumptions
For consistency, we assume that for each integration or script the folder containing it will have the same name as the integration/script name with no separators. For example the integration `Test Integration_Full-Name`, will be under `~/.../content/Packs/TestPack/Integrations/TestIntegrationFullName/`.

Integrations, Scripts and Playbooks directories that does not contain a yml file, will be overwritten automatically.
All other folders that do not contain a json file, will be overwritten automatically.
For clarity, the given pack should be consistent with Content hierarchy structure with no rouge files present.

We assume that test playbooks contain the `test` word in their name.

### Supported File Types
* Integrations
* Beta Integrations
* Scripts
* Playbooks
* Test Playbooks
* Reports
* Dashboards
* Widgets
* Incdient Fields
* Indicator Fields
* Incident Types
* Layouts
* Classifiers

### Not Supported
Integrations / Scripts written in JavaScript.

### Examples
```
demisto-sdk download -o Packs/TestPack -i "Test Integration" -i "TestScript" -i "TestPlaybook"
```
This will download the integration `Test Integration`, script `TestScript` & playbook `TestPlaybook` only if they don't exists in the output pack.
<br/><br/>
```
demisto-sdk download -o Packs/TestPack -i "Test Integration" -i "TestScript" -i "TestPlaybook" -f
```
This will download the integration `Test Integration`, script `TestScript` & playbook `TestPlaybook`.
If one of the files exists in the output pack, only its changes from Demisto instance will be merged into the existing.
If the file doesn't exist in the output pack, it will be copied completely from Demisto instance.
<br/><br/>
```
demisto-sdk download -o Packs/TestPack -a
```
This will download the all available custom content to the output pack.
-i / --input should not be provided.
<br/><br/>
```
demisto-sdk download -lf
```
This will print the list of all custom content files available to be downloaded from Demisto instance.
-i / --input & -o / --output should not be provided.
<br/><br/>
