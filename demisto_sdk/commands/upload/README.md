## Upload

**Upload an integration to Demisto.**

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Demisto base URL, and `DEMISTO_API_KEY` environment variable should contain a valid Demisto API Key.
To set the environment variables, run the following shell commands:
```
export DEMISTO_BASE_URL=<YOUR_DESMISTO_BASE_URL>
export DEMISTO_API_KEY=<YOUR_DEMISTO_API_KEY>
```


### Use Cases
This command is used in order to upload integration files to a remote Demisto instance. This is useful especially when developing a new integration, so that while working on the code you can upload it directly from the CLI and optimize the development process flow.


### Arguments
* **-i INTEGRATION_PATH, --inpath INTEGRATION_PATH**

    The path of an integration file or a package directory to upload

* **-k, --insecure**

    Skip certificate validation

* **-v, --verbose**

    Verbose output


### Examples
```
demisto-sdk upload -i Integrations/GoogleCloudTranslate/integration-GoogleCloudTranslate.yml
```
This will upload the integration YML file `integration-GoogleCloudTranslate.yml` to the Demisto instance.
<br/><br/>
```
demisto-sdk upload -i Integrations/GoogleCloudTranslate
```
This will create a temporary unified file of the `GoogleCloudTranslate` integration which will be uploaded to the Demisto instance.
<br/><br/>
```
demisto-sdk upload -i Integrations/GoogleCloudTranslate/integration-GoogleCloudTranslate.yml -k
```
This will upload the integration YML file `integration-GoogleCloudTranslate.yml` to the Demisto instance, without a certificate validation.
<br/><br/>
```
demisto-sdk upload -i Integrations/GoogleCloudTranslate/integration-GoogleCloudTranslate.yml -v
```
This will upload the integration YML file `integration-GoogleCloudTranslate.yml` to the Demisto instance and print a JSON representation of the integration.
