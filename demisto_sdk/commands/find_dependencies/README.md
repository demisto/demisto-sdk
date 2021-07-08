## Unify

Find pack dependencies and update pack metadata.

**Use Cases**:
This command is used in order to find the dependencies between packs and to update the dependencies section in the pack metadata.

**Arguments**:
* **-i, --input**
  Pack path to find dependencies. For example: Pack/HelloWorld
* **-idp, --id-set-path**
  Path to id set json file.
* **--no-update**
  Use to find the pack dependencies without updating the pack metadata.
* **-v, --verbose**
  Whether to print the log to the console.
* **--use-pack-metadata**
  Whether to update the dependencies from the pack metadata.

**Examples**:
`demisto-sdk find-dependencies -i Integrations/MyInt`
This will calculate the dependencies for the `MyInt` pack and update the pack_metadata.
