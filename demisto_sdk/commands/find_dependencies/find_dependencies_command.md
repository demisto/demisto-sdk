## find-dependencies
Find pack dependencies and update pack metadata.

**Use-Cases**:
This command is used for calculating pack dependencies and updating the pack metadata with found result.

**Arguments**:
* **-p, --pack_folder_name** Pack folder name to calculate dependencies.
* **-i, --id_set_path** ID set json full path, mainly for skipping creation of id set.

**Examples**:
`demisto-sdk find-dependencies -p ImpossibleTraveler`
Navigate to content repository root folder before running find-dependencies command.
