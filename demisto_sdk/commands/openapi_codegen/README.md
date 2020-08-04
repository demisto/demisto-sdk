## OpenAPI Code-gen

**Generate a Cortex XSOAR integration from an OpenAPI (Swagger) file.**

### Arguments

* **'-h', '--help'**

    Show command help.

* **'-i', '--input_file'**

    The swagger file to load in JSON format.

* **'-cf', '--config_file'**

    The integration configuration file. It is created in the first run of the command.

* **'-n', '--base_name'**

    The base filename to use for the generated files.

* **'-o', '--output_dir'**

    Directory to store the output in (default is current working directory).

* **'-pr', '--command_prefix'**

    Add a prefix to each command in the code.

* **'-c', '--context_path'**

    Context output path.

* **'-u', '--unique_keys'**

    Comma separated unique keys to use in context paths (case sensitive).

* **'-r', '--root_objects'**

    Comma separated JSON root objects to use in command outputs (case sensitive).

* **'-v', '--verbose'**

    Be verbose with the log output.

* **'-f', '--fix_code'**

    Fix the python code using autopep8.

* **'-a', '--use_default'**

    Use the automatically generated integration configuration (Skip the second run).

### Examples
```
demisto-sdk openapi-codegen -i pet_swagger.json -n PetStore -o PetStoreIntegration -u "id" -r "Pet"
```

This will create an integration configuration for the PetStore swagger file in the `PetStoreIntegration` directory.
It will use `id` to identify unique properties in outputs and `Pet` to identify root objects in the outputs.
That configuration can be modified and will be used in a second run of the command.
<br/>
```
demisto-sdk openapi-codegen -i pet_swagger.json -n PetStore -o PetStoreIntegration -u "id" -r "Pet" -cf "PetStoreIntegration/PetStore.json"
```

This will create the Cortex XSOAR integration for the PetStore swagger file using the configuration file located in PetStoreIntegration/PetStore.json.
<br/>
 ```
demisto-sdk openapi-codegen -i pet_swagger.json -n PetStore -o PetStoreIntegration -u "id" -r "Pet" -a
```

This will create the Cortex XSOAR integration for the PetStore swagger file using the generated configuration file, thus skipping the second run of the command.
<br/><br/>
After running these commands, the generated Cortex XSOAR integration will be available in package format.
It will be available for use in the Cortex XSOAR system using `demisto-sdk upload` to upload it.
