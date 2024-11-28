## openapi-codegen
### Overview
It is possible to generate a Cortex XSOAR integration package (YAML and Python files) with a dedicated tool in the Cortex XSOAR (demisto) SDK.
The integration will be usable right away after generation.

**Requirements**
* OpenAPI (Swagger) specification file (v2.0 is recommended) in JSON format.
* Cortex XSOAR (demisto) SDK

### Options

* **'-h', '--help'**

    Show command help.

* **'-i', '--input_file'**

    The Postman collection 2.1 JSON file.

* **'-op', '--output-prefix'**

    ets the global integration output prefix. Default is the integration name without spaces and special characters.

* **'-n', '--name'**

    The output integration name.

* **'-o', '--output_dir'**

    Directory to store the output in (default is current working directory).

* **'-cp', '--command_prefix'**

    The prefix for every command in the integration. Default is the integration name in lower case.

* **'-p', '--package'**

    Generated integration will be split to package format instead of a yml file.

* **'--config-out'**

    Used for advanced integration customisation. Generates a config json file instead of integration.

#### Examples
The Examples below are for the [Pet Store Swagger specification](https://petstore.swagger.io/).

```
demisto-sdk openapi-codegen -i pet_swagger.json -n PetStore -o PetStoreIntegration -u "id" -r "Pet"
```

This will create an integration configuration for the PetStore swagger file in the `PetStoreIntegration` directory.
It will use `id` to identify unique properties in outputs and `Pet` to identify root objects in the outputs.
That configuration can be modified and will be used in a second run of the command.

```
demisto-sdk openapi-codegen -i pet_swagger.json -n PetStore -o PetStoreIntegration -u "id" -r "Pet" -cf "PetStoreIntegration/PetStore.json"
```

This will create the Cortex XSOAR integration for the PetStore swagger file using the configuration file located in PetStoreIntegration/PetStore.json.

 ```
demisto-sdk openapi-codegen -i pet_swagger.json -n PetStore -o PetStoreIntegration -u "id" -r "Pet" -a
```

This will create the Cortex XSOAR integration for the PetStore swagger file using the generated configuration file, thus skipping the second run of the command.


### Video Tutorial
<video controls>
    <source src="https://github.com/demisto/content-assets/raw/master/Assets/OpenAPICodegen/openapicodegen.mp4"
            type="video/mp4"/>
    Sorry, your browser doesn't support embedded videos. You can download the video at: https://github.com/demisto/content-assets/raw/master/Assets/OpenAPICodegen/openapicodegen.mp4
</video>
