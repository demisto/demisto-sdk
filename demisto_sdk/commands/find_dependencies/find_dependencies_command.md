## find-dependencies
Find pack dependencies and update pack metadata.

**Use-Cases**:
This command is used for calculating pack dependencies and updating the pack metadata with found result.

**Arguments**:
* **-i, --input** Pack path name to calculate dependencies.
* **-ids, --id_set_path** ID set json full path, mainly for skipping creation of id set.
* **--no-update** Use to find the pack dependencies without updating the pack metadata.
* **-v, --verbose** Whether to print the log to the console.
* **--all-packs-dependencies** Return a json file with ALL content packs dependencies. The json file will be saved under the path given in the '--output-path' argument.
* **-o, --output-path** The destination path for the packs dependencies json file. This argument only works  when using either the `--all-packs-dependencies` or `--get-dependent-on` flags.
**Examples**:
`demisto-sdk find-dependencies -i Packs/ImpossibleTraveler`
Navigate to content repository root folder before running find-dependencies command.
