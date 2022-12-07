## Find Dependencies

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
* **--all-packs-dependencies**
  Return a json file with ALL content packs dependencies. The json file will be saved under the path given in the '--output-path' argument.
* **-o, --output-path**
  The destination path for the packs dependencies json file. This argument only works  when using either the `--all-packs-dependencies` or `--get-dependent-on` flags.
* **--get-dependent-on**
  Get only the packs dependent ON the given pack. Note: this flag can not be used for the packs ApiModules and Base.
* **-d --dependency**
  Find which items in a specific content pack appears as a mandatory dependency of the searched pack.

**Examples**:
`demisto-sdk find-dependencies -i Integrations/MyInt`
This will calculate the dependencies for the `MyInt` pack and update the pack_metadata.
