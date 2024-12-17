## Download

**Downloads and merges content from a Cortex XSOAR or Cortex XSIAM tenant to your local repository.**

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Cortex XSOAR/XSIAM instance URL,
and `DEMISTO_API_KEY` environment variable should contain a valid Cortex XSOAR/XSIAM API Key.

**Notes for Cortex XSIAM or Cortex XSOAR 8.x:**
- Cortex XSIAM Base URL should be retrieved from XSIAM instance -> Settings -> Configurations -> API Keys -> `Copy URL` button in the top right corner, and not the browser URL.
- API key should be of a `standard` security level, and have the `Instance Administrator` role.
- To use the command the `XSIAM_AUTH_ID` environment variable should also be set.


To set the environment variables, run the following shell commands:
```
export DEMISTO_BASE_URL=<YOUR_DESMISTO_BASE_URL>
export DEMISTO_API_KEY=<YOUR_DEMISTO_API_KEY>
```
and for Cortex XSIAM or Cortex XSOAR 8.x
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
This command is useful when developing within the Cortex tenant itself and downloading the new entities to your local environment in order to continue with the contribution process.


### Notes and Limitations
* The download is one-directional; data goes from the server to the repository.

* JavaScript's integrations and scripts are not downloadable using this command.

* If there are files that exist both in the output directory and are specified in the input, they are ignored. To override this behavior so that existing files are merged with their newer version, use the --force/-f flag.

* For consistency, we assume that for each integration or script, the folder containing it has the same name as the integration/script name with no separators. For example. the integration Test Integration_Full-Name, is under ~/.../Packs/TestPack/Integrations/TestIntegrationFullName/.

* Integrations, scripts and playbook directories that do not contain a YAML file are overwritten automatically. All other folders that do not contain a JSON file are overwritten automatically. To keep things clear and consistent, the given pack should be consistent with the content hierarchy structure with no rouge files present.

* The SDK assumes the following playbooks as type TestPlaybook:

  * Playbooks with names that start with Test, Test_, test_, Test-, or test-
  * Playbooks with names that end with Test,_test or -test.

### Arguments
* **-o, --output**

    A path of a package directory to download custom content to.

* **-i, --input**

    Custom content file name to be downloaded. Can be provided multiple times. File names can be retrieved using the -lf flag.

* **-lf, --list-files**

    List all custom content items available to download.

* **-a, --all-custom-content**

    Download all available custom content files.

* **-fmt, --run-format**

    Whether to run Demisto SDK formatting on downloaded files.

* **-f, --force**

    Whether to override existing files.

* **--insecure**

    Skip certificate validation.

* **-r, --regex**

    Regex Pattern. When specified, download all the custom content files with a name that matches this regex pattern.

* **--system**

    Download system items.

* **--it, --item-type**

    Type of the content item to download, use only when downloading system items.

* **--auto-replace-uuids/--no-auto-replace-uuids**
  If False, avoid UUID replacements when downloading using the download command. The default value is True.
* **--init** Initialize the output directory with a pack structure.
* **--keep-empty-folders** Keep empty folders when a pack structure is initialized.


### Supported File Types
* Integrations
* Beta Integrations
* Scripts
* Playbooks
* Test Playbooks
* Reports
* Dashboards
* Widgets
* Incident Fields
* Indicator Fields
* Incident Types
* Layouts
* Classifiers
* Lists

#### Note:
The following are not supported:
- Integrations / Scripts written in JavaScript.
- A playbook that starts with the word 'Test', it would be downloaded as a test playbook.

### Examples
```
demisto-sdk download -o Packs/TestPack -i "Test Integration" -i "TestScript" -i "TestPlaybook"
```
Downloads the integration `Test Integration`, script `TestScript`, and playbook `TestPlaybook` only if they don't exist in the output pack.
<br/><br/>
```
demisto-sdk download -o Packs/TestPack -i "Test Integration" -i "TestScript" -i "TestPlaybook" -f
```
Download the integration `Test Integration`, script `TestScript` & playbook `TestPlaybook`.
If one of the files exists in the output pack, only its changes from the Cortex XSOAR instance are merged into the existing.
If the file doesn't exist in the output pack, it will be copied completely from Cortex XSOAR instance.
<br/><br/>
```
demisto-sdk download -o Packs/TestPack -a
```
Download the all available custom content to the output pack; -i / --input should not be provided.
<br/><br/>
```
demisto-sdk download -lf
```
Print the list of all custom content files available to be downloaded from Cortex XSOAR instance;
-i / --input and -o / --output should not be provided.
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
