## Download

**Download & merge custom content from Demisto instance to local content repository.**

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Cortex XSOAR/XSIAM instance URL,
and `DEMISTO_API_KEY` environment variable should contain a valid Cortex XSOAR/XSIAM API Key.
To use the command on Cortex XSIAM the `XSIAM_AUTH_ID` environment variable should also be set.
To set the environment variables, run the following shell commands:
```
export DEMISTO_BASE_URL=<YOUR_DESMISTO_BASE_URL>
export DEMISTO_API_KEY=<YOUR_DEMISTO_API_KEY>
```
and for Cortex XSIAM
```
export XSIAM_AUTH_ID=<THE_XSIAM_AUTH_ID>
```
Note!
As long as `XSIAM_AUTH_ID` environment variable is set, SDK commands will be configured to work with an XSIAM instance.
In order to set Demisto SDK to work with Cortex XSOAR instance, you need to delete the XSIAM_AUTH_ID parameter from your environment.
```bash
unset XSIAM_AUTH_ID
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

* **-r, --regex**

    Regex Pattern. When specified, download all the custom content files with a name that matches this regex pattern.

* **--system**

    Download system items.

* **--it, --item-type**

    The items type to download, use just when downloading system items.

* **--auto-replace-uuids/--no-auto-replace-uuids**
  If False, avoid UUID replacements when downloading using the download command. The default value is True.

### Asumptions
For consistency, we assume that for each integration or script the folder containing it will have the same name as the integration/script name with no separators. For example the integration `Test Integration_Full-Name`, will be under `~/.../Packs/TestPack/Integrations/TestIntegrationFullName/`.

Integrations, Scripts and Playbooks directories that does not contain a yml file, will be overwritten automatically.
All other folders that do not contain a json file, will be overwritten automatically.
For clarity, the given pack should be consistent with Content hierarchy structure with no rouge files present.

The SDK assumes the following playbooks as type TestPlaybook:
- Playbooks whose name starts with either `Test`, `Test_`, `test_`, `Test-`, or `test-`
- Playbooks whose name ends with either `Test`,`_test` or `-test`.


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
* Lists

### Not Supported
Integrations / Scripts written in JavaScript.
A playbook that starts with the word 'Test', it would be downloaded as a test playbook.

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
```
demisto-sdk download -o Packs/Phishing -r *Pishing*
```
Regex Pattern. When specified, download all the custom content files with a name that matches this regex pattern.
-o / --output should not be provided.
<br/><br/>
```
demisto-sdk download --system -it IncidentType -i "Authentication" -i "Access" -o Packs/ABCD
```
Download system items, should provide the item type, and the item name as input.
<br/><br/>
