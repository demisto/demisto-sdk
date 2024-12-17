## postman-codegen
### Overview
Use the `demisto sdk postman-codegen` command to generate an XSOAR integration (yml file) from a Postman Collection v2.1. Note the generated integration is in the yml format. Use the `demisto-sdk split` [command](package-dir#split-a-yml-file-to-directory-structure) to split the integration into the recommended [Directory Structure](package-dir) for further development.

You can generate the integration either as a two-step process or a single step.
- **Single Step:** Use this method to generate directly an integration yml file.
- **Two Steps:** Use this method for more configuration and customization of the generated integration and code.
    1. Generate an integration config file.
    2. Update the config file as needed. Then generate the integration from the config file using the `demisto-sdk generate-integration` command.

### Options
*  **-h, --help**
*  **-i, --input**  
    Postman collection 2.1 JSON file
*  **-o, --output**  
   (Optional) The output directory. Default is the current directory.
*  **-n, --name**  
   (Optional) Sets the integration name.
*  **-op, --output-prefix**  
   (Optional) Sets the global integration output prefix. Default is the integration name without spaces and special characters.
*  **-cp, --command-prefix**  
   (Optional) The prefix for every command in the integration. Default is the integration name in lower case.
*  **--config-out**  
   (Optional) If passed, generates config json file for further integration customisation.

## How the command converts Postman collection
- Collection name converts to integration name.
- Collection name converts to command prefix (if command prefix is not passed).
  - Example: **Virus Total** -> **virus-total**
- Collection name converts to prefix of each command output.
  - Example: **Virus&& Total** -> **VirusTotal.Scan.scan_id**
- Collection request name converts to integration command.
  - Example: **Get Hosts** -> **get-hosts**
- Authentication
    - Base authentication type converts to username/password parameter
    - API Key authentication type converts to apikey encrypted parameter
    - Bearer token authentication type converts to apikey encrypted parameter
- Request name converts to command name. Example: **Get Events** -> **get-events**
- Request url variables converts to command arguments and passed as part of the request url. Example: *https://virustotal.com/vtapi/v2/ip/{{ip}}* -> created **ip** argument -> *https://virustotal.com/vtapi/v2/ip/8.8.8.8*
- Request query parameters converts to command arguments. Example: *https://virustotal.com/vtapi/v2/ip?resource=8.8.8.8* -> created **resource** argument -> *https://virustotal.com/vtapi/v2/ip?resource=8.8.8.8*
- Path URL variable converts to command argument and passed as a part of the request URL. Example: *https://virustotal.com/vtapi/v2/ip/:ip* -> creates **ip** argument -> *https://virustotal.com/vtapi/v2/ip/8.8.8.8* if `:ip` path variable equals 8.8.8.8.
- Request body - each leaf value converts to command argument and **body_format** which will allow further body customisation. Example: `{"key1":"val1","key2":{"key3":"val3"}}` -> created **key1** and **key3** arguments and **body_format** with the following value `{"key1":"{{key1}}","key2":{"key3":"{{key3}}"}}`
- Response JSON output converts to command outputs.

## Postman Collection Requirements
### Mandatory Requirements
- Collection v2.1 is supported
- Each request should be saved and contain at least one successful response (which also saved)
- If url contains variables like *https://virustotal.com/vtapi/v2/ip/8.8.8.8*, then make sure to set it as variable like *https://virustotal.com/vtapi/v2/ip/{{ip}}*
- Define the authentication method under Collection edit page -> Authorization section
  - Under collection settings, Authorization section should be set (recommended way)
  - Requests must contain Authorization header


### Optional Requirements
- Collection description
- Short request names **Get Endpoints** will convert to **get-endpoints**
- Set description to request

## How to run
- `demisto-sdk postman-codegen -i VirusTotal.collection.json --name 'Virus Total' --command-prefix vt`  
  The above command do the following:
    - Sets the name of the integration to `Virus Total`.
    - Sets the commands prefix to `vt` (`vt-get-url`, `vt-scan-url`).
    - Generates `integration-VirusTotal.yml` file in the current directory.

- `demisto-sdk postman-codegen -i VirusTotal.collection.json --name 'Virus Total' -o /output/path --config-out`  
  The above command do the following:
    - Generates `config-VirusTotal.json` file under `/output/path` directory.
    - Sets the name of the integration `Virus Total`.

## Tutorial Video:
<video controls>
    <source src="https://github.com/demisto/content-assets/raw/master/Assets/PostmanCodegen/postman-codegen-tutorial.mp4"
            type="video/mp4"/>
    Sorry, your browser doesn't support embedded videos. You can download the video at: https://github.com/demisto/content-assets/raw/master/Assets/PostmanCodegen/postman-codegen-tutorial.mp4
</video>

## Example files:
* [URLScan Postman Collection v2.1](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/postman_codegen/resources/urlscan.io.postman_collection.json)
* [URLScan generated config file](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/postman_codegen/resources/config-urlscanio.json)
* [URLScan generated integration yml](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/postman_codegen/resources/integration-urlscanio.yml)
