## Generate XSOAR Integration from XSOAR integration config file.

### Overview
Use the generate-integration command to generate a Cortex XSIAM/Cortex XSOAR integration from an integration config JSON file.
The JSON config file can be generated from a Postman collection via the postman-codegen command.

### Options
* **-i, --input** config json file produced by commands like postman-codegen and openapi-codegen.
* **-o, --output**The output directory to save the integration package.

For more information see docs [here](https://docs-cortex.paloaltonetworks.com/r/1/Demisto-SDK-Guide/generate-integration)
