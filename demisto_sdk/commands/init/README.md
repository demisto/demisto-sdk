## init
Create a pack, integration or script template.

**Use-Cases**
* This command is used to ease the initial creation of a pack, integration or a script.

**Arguments**:
* **-n, --name** The name given to the files and directories of new pack/integration/script being created
* **--id** The id used for the yml file of the integration/script
* **-o, --output** The output directory to which the created object will be saved
* **--integration** Create an integration
* **--script** Create a script
* **--pack** Create a pack
* **-t, --template** Create an Integration/Script based on a specific template.

**Notes**
* If `integration` or `script` not set - the command will automatically create a pack, even if `pack` was not set.
* If a `name` will not be given, a prompt will show asking for an input -
A pack, integration or script can not be created without a given `name`.
* The `name` parameter *can not* have spaces (' ') in it.
* If no `id` will be given and an integration or script is being created, a prompt will show asking for an input.
You may choose to use the `name` parameter as the `id` for the yml file, or provide a different identifier.
* The `id` parameter *can* have spaces (' ') in it.
* If activated from content repository and no `output` given - A pack will be created in the "Packs" directory.
* If activated from content repo or within a pack directory and no `output` given -
An integration will be created in the "Integrations" directory and a script will be created in the "Scripts" repository.
* If no `output` given and the command is not activated from content repo nor a pack directory -
The pack/integration/script will be created in your current working directory.
* The default templates are based on "StarterPack/BaseIntegration" and "StarterPack/BaseScript" found in content repo.

**Examples**

*Note: the below example commands and explanations are given as though the command is activated from the content repo directory.*


`demisto-sdk init -n My_Pack`

This will create a new pack named "My_Pack" under the "Packs" directory in content repo.


`demisto-sdk init --integration -n MyNewIntegration -o path/to/my/dir`

This will create a new integration template named MyNewIntegration within "path/to/my/dir" directory.


`demisto-sdk init --script --id "My Script ID" -n MyScript`

This will create a named "MyScript" under the "Scripts" directory and the yml file will have the id "My Script ID".


`demisto-sdk init --pack -n My_Pack`

This will create a new pack named "My_Pack" under the "Packs" directory in content repo.
