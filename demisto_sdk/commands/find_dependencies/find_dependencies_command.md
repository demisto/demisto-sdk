## find-dependencies
Find pack dependencies and update pack metadata.

**Use-Cases**:
This command is used for calculating pack dependencies and updating the pack metadata with found result.

**Arguments**:
* **-i, --input** Pack path name to calculate dependencies.
* **-ids, --id_set_path** ID set json full path, mainly for skipping creation of id set.
* **--no-update** Use to find the pack dependencies without updating the pack metadata.
* **-v, --verbose** Whether to print the log to the console.

**Examples**:
`demisto-sdk find-dependencies -i Packs/ImpossibleTraveler`
Navigate to content repository root folder before running find-dependencies command.
