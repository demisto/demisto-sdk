## Upload

**Upload a content entity to Cortex XSOAR/XSIAM.**

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Cortex XSOAR/XSIAM instance URL,
and `DEMISTO_API_KEY` environment variable should contain a valid Cortex XSOAR/XSIAM API Key.

**Notes for Cortex XSIAM or Cortex XSOAR 8.x:**
- Cortex XSIAM Base URL should be retrieved from XSIAM instance -> Settings -> Configurations -> API Keys -> `Copy URL` button on the top rigth corner, and not the browser URL.
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
This command is used in order to upload content entities to a remote Demisto instance.
Supported content entities:
- Integrations
- Playbooks
- Scripts
- Widgets
- Dashboards
- Incident Types
- Incident Fields
- Indicator Fields
- Layouts
- Layouts Container
- Classifiers
- Packs
- Zipped packs
- Reports

#### Limitation
Uploading classifiers to Cortex XSOAR is available from version 6.0.0 and up.

### Arguments
* **-i <PATH_IN_CONTENT>, --input --<PATH_IN_CONTENT>**

    Where PATH_IN_CONTENT is one of the following:
    1. Pack
    2. Directory inside a pack for example: Playbooks
    3. Directory containing an integration or a script data for example: HelloWorld
    4. Valid file that can be imported to Cortex XSOAR manually For example a playbook: HelloWorld.yml
    5. Path to zipped pack (may located outside the Content directory)

* **-z, --zip**

    in case a pack was passed in the -i argument or using `--input-config-file` argument - zip the pack before upload.
    Defauts to `true`.

* **--nz, --no-zip**

    Will not zip the pack and will upload the content items, item by item as custom content.

* **--keep-zip <DIRECTORY_FOR_THE_ZIP>**

    in case a pack was passed in the -i argument and -z is used, DIRECTORY_FOR_THE_ZIP is where to store the zip after creation.

* **--override-existing**

    If true, will skip the override confirmation prompt while uploading packs.

* **--insecure**

    Skip certificate validation

* **-v, --verbose**

    Verbose output - The argument -v is deprecated. Use --console-log-threshold or --file-log-threshold instead.

* **--input-config-file**

    The path to the config file to download all the custom packs from

* **--skip-validation**

    if true will skip all upload packs validations, use just when migrate existing custom content entities to custom content packs to override all the entities with the packs.

* **-x, --xsiam**

    uploads the pack to a XSIAM server. Must be used together with -z

* **--console-log-threshold**

    Minimum logging threshold for the console logger. Possible values: DEBUG, INFO, WARNING, ERROR.

* **--file-log-threshold**

    Minimum logging threshold for the file logger. Possible values: DEBUG, INFO, WARNING, ERROR.

### Examples
```
demisto-sdk upload -i Packs/HelloWorld/Integrations/HelloWorld/
```
This will create a unified **integration** YML file and will upload it to the Cortex XSOAR instance.
<br/><br/>
```
demisto-sdk upload -i Packs/HelloWorld/Scripts/HelloWorldScript
```
This will create a temporary unified file of the `HelloWorldScript` **script** which will be uploaded to the Cortex XSOAR instance.
<br/><br/>

```
demisto-sdk upload -i Packs/HelloWorld/Scripts
```
This will iterate over the **scripts** folder under the `HelloWorld` pack and in turn will create a temporary unified file for each script and upload it to the Cortex XSOAR instance.
<br/><br/>

```
demisto-sdk upload -i Packs/HelloWorld
```
This will iterate over **all content entities** under the pack `HelloWorld` and will and in turn will upload each entity to the Cortex XSOAR instance.
<br/><br/>
```
demisto-sdk upload -i Packs/HelloWorld -z
```
This will zip the pack `HelloWorld` and will upload the zip file `uploadable_packs.zip` as a pack to the designated Cortex XSOAR Marketplace.
<br/><br/>
```
demisto-sdk upload -i Packs/HelloWorld -z --keep-zip some/directory
```
This will zip the pack `HelloWorld` in `some/directory/uploadable_packs.zip` directory and will upload the zip file as a pack to the designated Cortex XSOAR Marketplace.
<br/><br/>
```
demisto-sdk upload -i path/to/HelloWorld.zip
```
This will upload the zipped pack `HelloWorld.zip` to the Cortex XSOAR instance.
<br/><br/>
```
demisto-sdk upload -i Integrations/GoogleCloudTranslate/integration-GoogleCloudTranslate.yml --insecure
```
This will upload the integration YML file `integration-GoogleCloudTranslate.yml` to the Cortex XSOAR instance, **without a certificate validation**.
<br/><br/>
```
demisto-sdk upload -i Integrations/GoogleCloudTranslate/integration-GoogleCloudTranslate.yml --verbose
```
This will upload the integration YML file `integration-GoogleCloudTranslate.yml` to the Cortex XSOAR instance and **print the response returned from the API**.
```
demisto-sdk upload --input-config-file demisto_sdk/commands/upload/tests/data/xsoar_config.json
```
This will upload the custom packs from the config file, a custom pack can be zipped file or unzipped file.
<br/><br/>
```
demisto-sdk upload -i Packs/HelloWorld -z --skip-validation
```
This will zip the pack `HelloWorld` and will upload without any validation the zip file `uploadable_packs.zip` as a pack to the designated Cortex XSOAR Marketplace.
This `skip validation` parameter is for migration from custom content entities to custom content packs.
<br/><br/>

```
demisto-sdk upload -i Packs/HelloWorld -z --xsiam
```
This will zip the pack `HelloWorld` and will upload it to the XSIAM server Marketplace page.
<br/><br/>
