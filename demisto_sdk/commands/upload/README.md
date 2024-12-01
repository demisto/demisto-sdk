## Upload

### Overview

**Upload a content entity to Cortex XSOAR/XSIAM.**

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

### Options
* **-i, --input**

    The path of file or a directory to upload. The following are supported:
    1. Pack
    2. Directory inside a pack for example: Integrations
    3. Directory containing an integration or a script data for example: HelloWorld
    4. Valid file that can be imported to Cortex XSOAR manually For example a playbook: HelloWorld.yml
    5. Path to zipped pack (may locate outside the Content directory)

* **-z/-nz, --zip/--no-zip**

    Compress the pack to zip before upload, this flag is relevant only for packs.

* **--keep-zip**

    Directory where to store the zip after creation, this argument is relevant only for packs and in case the --zip flag is used.

* **--override-existing**

    This value (True/False) determines if the user should be presented with a confirmation prompt when attempting to upload a content pack that is already installed on the Cortex XSOAR server. This allows the upload command to be used within non-interactive shells.

* **--insecure**

    Skip certificate validation

* **--input-config-file**

    The path to the config file to download all the custom packs from

* **--skip-validation**

    Only for upload zipped packs, if true will skip upload packs validation, use just when migrate existing custom content to packs.

* **-x, --xsiam**

    uploads the pack to a XSIAM server. Must be used together with -z

* **--console-log-threshold**

    Minimum logging threshold for the console logger. Possible values: DEBUG, INFO, WARNING, ERROR.

* **--file-log-threshold**

    Minimum logging threshold for the file logger. Possible values: DEBUG, INFO, WARNING, ERROR.
* **-tpb**

    Adds the test playbook for upload when the -tpb flag is used. This flag is relevant only for packs.
* **-mp, --marketplace**

    The marketplace to which the content will be uploaded.
* **--reattach**

    Reattach the detached files in the XSOAR instance for the CI/CD Flow. If you set the --input-config-file flag, any detached item in your XSOAR instance that isn't currently in the repo's SystemPacks folder will be re-attached.

### Supported content entities for upload:
You can upload these content entities to a remote instance.
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

### Examples
```
demisto-sdk upload -i Packs/HelloWorld/Integrations/HelloWorld/
```
Creates a unified **integration** YML file and will upload it to the Cortex XSOAR instance.
<br/><br/>
```
demisto-sdk upload -i Packs/HelloWorld/Scripts/HelloWorldScript
```
Creates a temporary unified file of the `HelloWorldScript` **script** which will be uploaded to the Cortex XSOAR instance.
<br/><br/>

```
demisto-sdk upload -i Packs/HelloWorld/Scripts
```
Iterates over the **scripts** folder under the `HelloWorld` pack and in turn will create a temporary unified file for each script and upload it to the Cortex XSOAR instance.
<br/><br/>

```
demisto-sdk upload -i Packs/HelloWorld
```
Iterates over **all content entities** under the pack `HelloWorld` and will and in turn will upload each entity to the Cortex XSOAR instance.
<br/><br/>
```
demisto-sdk upload -i Packs/HelloWorld -z
```
Zips the pack `HelloWorld` and will upload the zip file `uploadable_packs.zip` as a pack to the designated Cortex XSOAR Marketplace.
<br/><br/>
```
demisto-sdk upload -i Packs/HelloWorld -z --keep-zip some/directory
```
Zips the pack `HelloWorld` in `some/directory/uploadable_packs.zip` directory and will upload the zip file as a pack to the designated Cortex XSOAR Marketplace.
<br/><br/>
```
demisto-sdk upload -i path/to/HelloWorld.zip
```
Uploads the zipped pack `HelloWorld.zip` to the Cortex XSOAR instance.
<br/><br/>
```
demisto-sdk upload -i Integrations/GoogleCloudTranslate/integration-GoogleCloudTranslate.yml --insecure
```
Uploads the integration YML file `integration-GoogleCloudTranslate.yml` to the Cortex XSOAR instance, **without a certificate validation**.
<br/><br/>
```
demisto-sdk upload -i Integrations/GoogleCloudTranslate/integration-GoogleCloudTranslate.yml --verbose
```
Uploads the integration YML file `integration-GoogleCloudTranslate.yml` to the Cortex XSOAR instance and **print the response returned from the API**.
```
demisto-sdk upload --input-config-file demisto_sdk/commands/upload/tests/data/xsoar_config.json
```
Uploads the custom packs from the config file, a custom pack can be zipped file or unzipped file.
<br/><br/>
```
demisto-sdk upload -i Packs/HelloWorld -z --skip-validation
```
Zips the pack `HelloWorld` and will upload without any validation the zip file `uploadable_packs.zip` as a pack to the designated Cortex XSOAR Marketplace.
This `skip validation` parameter is for migration from custom content entities to custom content packs.
<br/><br/>

```
demisto-sdk upload -i Packs/HelloWorld -z --xsiam
```
Zips the pack `HelloWorld` and will upload it to the XSIAM server Marketplace page.
<br/><br/>
