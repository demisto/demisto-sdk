## Generate XSOAR Integration from Postman Collection v2.1

**Arguments**:
* **-i, --input** The Postman collection 2.1 JSON file.
* **-o, --output** The output directory to save the config file or the integration.
* **-n, --name** The output integration name.
* **-op, --output-prefix** The global integration output prefix. By default, it is the product name.
* **-cp --command-prefix** The prefix for each command in the integration. By default, is the product name in lower case.
* **-config-out** Used for advanced integration customisation. Generates a config json file instead of integration.
* **-p --package** Generated integration will be split to package format instead of a yml file.

For more information see docs [here](https://xsoar.pan.dev/docs/integrations/postman-codegen)
