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
The force flag will cause all files already in the output directory to be merged with their newer version in server.

If the user won't use force, and there will be files existing both in the output package and in custom content, the file won't be downloaded.

### Arguments
* **-o PACK_PATH, --output Pack_PATH**

    The path of a package directory to download custom content to.

* **-i "file_name_1,...,file_name_n", --input "file_name_1,...,file_name_n"**

    Comma separated names of custom content files.

* **--insecure**

    Skip certificate validation.

* **-v, --verbose**

    Verbose output.

* **-f, --force**

    Whether to override existing files or not.


## Asumptions
We assume that if the user have an integration under his pack, the name of the directory where integration files are being
will be named as the file name without separators. For example, if the output pack is "~/.../content/Packs/TestPack",
and the integration name is "Test Integration", then the integration files will be under "~/.../content/Packs/TestPack/Integrations/TestIntegration/".

We assume that if the user already have a script/integration in the local content repository, it contains a yml file.


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
If the file exists in the output pack, only it's changes from Demisto instance will be merged into the file already in the repository.
If the file doesn't exist in the output pack, it will be copied completely from Demisto instace.
<br/><br/>
