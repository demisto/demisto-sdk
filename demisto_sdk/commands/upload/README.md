## Upload

**Upload a content entity to Demisto.**

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Demisto base URL, and `DEMISTO_API_KEY` environment variable should contain a valid Demisto API Key.
To set the environment variables, run the following shell commands:
```
export DEMISTO_BASE_URL=<YOUR_DESMISTO_BASE_URL>
export DEMISTO_API_KEY=<YOUR_DEMISTO_API_KEY>
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
- Layouts
- Classifiers

#### Limitation
Uploading classifiers to Cortex XSOAR is available from version 6.0.0 and up.

### Arguments
* **-i <PATH_IN_CONTENT>, --<PATH_IN_CONTENT>**

    Where PATH_IN_CONTENT is one of the following:
    1. Pack
    2. Directory inside a pack for example: Playbooks
    3. Directory containing an integration or a script data for example: HelloWorld
    4. Valid file that can be imported to Cortex XSOAR manually For example a playbook: HelloWorld.yml

* **--insecure**

    Skip certificate validation

* **-v, --verbose**

    Verbose output


### Examples
```
demisto-sdk upload -i Packs/HelloWorld/Integrations/HelloWorld/HelloWorld_unified.yml
```
This will upload the **integration** YML file `HelloWorld_unified.yml` to the Demisto instance.
<br/><br/>
```
demisto-sdk upload -i Packs/HelloWorld/Scripts/HelloWorldScript
```
This will create a temporary unified file of the `HelloWorldScript` **script** which will be uploaded to the Demisto instance.
<br/><br/>

```
demisto-sdk upload -i Packs/HelloWorld/Scripts
```
This will iterate over the **scripts** folder under the `HelloWorld` pack and in turn will create a temporary unified file for each script and upload it to the Demisto instance.
<br/><br/>

```
demisto-sdk upload -i Packs/HelloWorld
```
This will iterate over **all content entities** under the pack `HelloWorld` and will and in turn will upload each entity to the Demisto instance.
<br/><br/>

```
demisto-sdk upload -i Integrations/GoogleCloudTranslate/integration-GoogleCloudTranslate.yml --insecure
```
This will upload the integration YML file `integration-GoogleCloudTranslate.yml` to the Demisto instance, **without a certificate validation**.
<br/><br/>
```
demisto-sdk upload -i Integrations/GoogleCloudTranslate/integration-GoogleCloudTranslate.yml --verbose
```
This will upload the integration YML file `integration-GoogleCloudTranslate.yml` to the Demisto instance and **print the response returned from the API**.
