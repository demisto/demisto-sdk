## Generate XSOAR Integration from Postman Collection v2.1
The `postman-codegen` command is used to generate XSOAR integration from Postman Collection v2.1
It can happen in 2 steps or 1 step.
- 2 steps - allows more configuration and customization to the code. First step Postman collection will generate a config
file. You can update the config file [link](../generate_integration) and then run `demisto-sdk generate-integration -i config-YourIntegration.json`
- 1 step - will generate integration yml

Options:
*  **-h, --help**
    Show this message and exit.
*  **-i, --input**
    Postman collection 2.1 JSON file
*  **-o, --output**
   (Optional) The output directory to save the config file or integration yml. By default, set to current directory.
*  **-n, --name**
   (Optional) Set the integration name.
*  **-op, --output-prefix**
   (Optional) Set the global integration output prefix. By default, it is the integration name without spaces and special characters.
*  **-cp, --command-prefix**
   (Optional) The prefix for every command in the integration. By default, it is the integration name in lower case.
*  **--config**
   (Optional) If passed, generate config json file for further integration customisation.

### How it works
- Collection name converts to integration name.
- Collection name converts to command prefix (if command prefix is not passed). Example: **Virus Total** -> **virus-total**
- Collection name converts to prefix of each command output. For example: **Virus&& Total** -> **VirusTotal.Scan.scan_id**
- Collection request converts to integration command.
- Authentication
    - Base authentication type converts to username/password parameter
    - API Key authentication type converts to apikey encrypted parameter
- Request name converts to command name. Example: **Get Events** -> **get-events**
- Request url variables converts to command arguments and passed as part of the request url. Example: *https://virustotal.com/vtapi/v2/ip/{{ip}}* -> created **ip** argument -> *https://virustotal.com/vtapi/v2/ip/8.8.8.8*
- Request query parameters converts to command arguments. Example: *https://virustotal.com/vtapi/v2/ip?resource=8.8.8.8* -> created **resource** argument -> *https://virustotal.com/vtapi/v2/ip?resource=8.8.8.8*
- Request body - each leaf value converts to command argument and **body_format** which will allow further body customisation. Example: `{"key1":"val1","key2":{"key3":"val3"}}` -> created **key1** and **key3** arguments and **body_format** with the following value `{"key1":"{{key1}}","key2":{"key3":"{{key3}}"}}`
- Response JSON output converts to command outputs.

### Postman Collection Requirements
##### Mandatory Requirements
- Collection v2.1 is supported
- Each request should be saved and contain at least one successful response (which also saved)
- If url contains variables like *https://virustotal.com/vtapi/v2/ip/8.8.8.8*, then make sure to set it as variable like *https://virustotal.com/vtapi/v2/ip/{{ip}}*
- Define the authentication method under Collection edit page -> Authorization section
  - Under collection settings, Authorization section should be set (recommended way)
  - Requests must contain Authorization header


##### Optional Requirements
- Collection description
- Short request names **Get Endpoints** will convert to **get-endpoints**
- Set description to request

### Examples
- Generates `integration-VirusTotal.yml` file in the current directory, with name `Virus Total` and commands prefix `vt` (`vt-get-url`, `vt-scan-url`).
`demisto-sdk postman-codegen -i VirusTotal.collection.json --name 'Virus Total' --command-prefix vt`

- Generates `config-VirusTotal.json` file under `/output/path` directory.
`demisto-sdk postman-codegen -i VirusTotal.collection.json --name 'Virus Total' -o /output/path --config`
