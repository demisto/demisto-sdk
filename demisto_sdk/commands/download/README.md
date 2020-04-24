## Download

**Download & merge custom content from Demisto instance to local content repository.**

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Demisto base URL, and `DEMISTO_API_KEY` environment variable should contain a valid Demisto API Key.
To set the environment variables, run the following shell commands:
```
export DEMISTO_BASE_URL=<YOUR_DESMISTO_BASE_URL>
export DEMISTO_API_KEY=<YOUR_DEMISTO_API_KEY>
```


### Use Cases
This command is used in order to download & merge custom content from Demisto instance to local content repository. This is useful when developing custom content in Demisto instance and then to
download it to the local content repository in order to make a contribution.


## Behavior
The download is one-directional, data goes from the server to the repo.

If there are files that exist both in the output directory and are specified in the input, they will be ignored. To override this behavior such that existing files will be merged with their newer version, use the force flag.

### Arguments
* **-o PACK_PATH, --output Pack_PATH**

    The path of a package directory to download custom content to.

* **-i "FILE_NAME_1,...,FILE_NAME_n", --input "FILE_NAME_1,...,FILE_NAME_n"**

    Comma separated names of custom content files.

* **--insecure**

    Skip certificate validation.

* **-v, --verbose**

    Verbose output.

* **-f, --force**

    Whether to override existing files or not.


## Asumptions
For consistency, we assume that for each integration or script the folder containing it will have the same name as the integration/script name with any separators. For example the integration "Test Integration", will be under "~/.../content/Packs/TestPack/Integrations/TestIntegration/".

Integrations Scripts, and Playbooks folders that does not contain a yml file, will be overwritten automatically.
All other folders that do not contain a json file, will be overwritten automatically.
For clarity, the given pack should be consistent with Content hierarchy structure with no rouge files present.

### Examples
```
demisto-sdk download -o Pack/TestPack -i "Test Integration,TestScript,TestPlaybook"
```
This will download the integration "Test Integration", script "TestScript" & playbook "TestPlaybook" only if they don't exists in the output pack.
<br/><br/>
```
demisto-sdk download -o Pack/TestPack -i "Test Integration,TestScript,TestPlaybook" -f
```
This will download the integration "Test Integration", script "TestScript" & playbook "TestPlaybook".
If one of the files exists in the output pack, only its changes from Demisto instance will be merged into the existing.
If the file doesn't exist in the output pack, it will be copied completely from Demisto instance.
<br/><br/>
