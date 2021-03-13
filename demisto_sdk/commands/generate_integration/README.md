## Generate XSOAR Integration from XSOAR integration config file.
The `generate-integration` command is used to generate XSOAR integration from integration config json file generated
by commands like `postman-codegen` or `openapi-codegen`.

Options:
*  **-h, --help**
   Show this message and exit.
*  **-i, --input**
   config json file produced by commands like postman-codegen and openapi-codegen.
*  **-o, --output**
   (Optional) The output directory to save the integration yml. By default, set to current directory.

### Examples
Generates `integration-VirusTotal.yml` under `/output/path` directory.
`demisto-sdk generate-integration -i config-VirusTotal.json -o /output/path`

## Integration config json file
**Examples**
[Virus Total config file example]()

|Field Name|Field Type|Description|Examples|Is Required|
|----------|----------|-----------|--------|-----------|
|name|string|The integration name. The integration id will be generated from the name. Spaces and special characters will be removed|Virus Total|Required|
|command_prefix|string|The prefix to all the commands. According to the conventions command prefix should be lower cased and separated with dashes|vt,virustotal|Required|
|url|string|The default value for integration `Server URL` parameter.|https://www.virustotal.com|Optional|
|base_url_path|string|Suffix for the integration `Server URL` parameter. If the API url contains constant suffix like `/vtapi/v2`|vtapi/v2|Optional|
|auth|object|Determines which authentication method is used to connect to the method.||Optional|
|context_path|string|Prefix for every command outputs. Must not contain spaces nor special characters. |VirusTotal -> VirusTotal.IP.source|Required|
|fix_code|bool|If true, run autopep8 to format the Python code. The default and the recommneded value is `true`|true|Optional|
|commands|list|List of integration commands||Required|
|commands.name|string|Command name. Should be lower case and should not contain spaces nor special characters.|scan-file|Required|
|commands.context_path|string|Context path object for this specific command. For example if the command returns Report object, the set this field to `Report`|Report, IP, Event|Required|
|commands.root_object|string|In case you don't want to return the whole response as it is, and just a specific field of it.|result, scan|Optional|
|commands.unique_key|string|Unique/Identifier key field from the response/outputs.|id, sha1, name|Optional|
|commands.headers|list|Request headers|`[{"Content-Type": "application/json"},{"Accept": "application/json"}]`|Optional|
|commands.body_format|object|Defines the structure and the format of the request body. In case the request contains body, this field must be passed. Keys that wrapped with `{}` will be replaced with command args.|```{"user": {"name": "{user}", "id": "{id}", "status": "create"}```<br />`"{name}"` and `"{id}"` will be replaced with `name` and `id` command input args.|Optional|
|commands.arguments|list|||Optional|
|commands.arguments.in_|string|Possible values are `query` `url` `body`. If set to `query`, the argument will be passed in the request url query like `?resource={resource}`. If set to `body`, the argument will be passed in the request body. If set to `url`, the argument will be passed as part of the url like `/vtapi/v2/url/{resource}`|query, url, body|Required|
|commands.outputs|list||||



## Authentication
This section will define the way the integration will authenticate with 3rd party product/service.
**Example**
```json

```


## Parameters


## Arguments


## Outputs


## Request Body
