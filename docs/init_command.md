## init
Create a pack, integration or script template. If `--integration` and `--script` flags are not given the command will create a pack.

**Use-Cases**
This command is used to ease the initial creation of a pack, integration or a script.

**Arguments**:
* **-n, --name** The name given to the files and directories of new pack/integration/script being created
* **--id** The id used for the yml file of the integration/script
* **-o, --outdir** The directory to which the created object will be saved.
* **--integration** Create an integration
* **--script** Create a script
* **--pack** Create a pack

**Notes**
* If `integration` or `script` not set - the command will automatically create a pack, even if `pack` was not set.
* If a `name` will not be given, a prompt will show asking for an input -
A pack, integration or script can not be created without a given `name`.
* The `name` parameter *can not* have spaces (' ') in it.
* If no `id` will be given and an integration or script is being created, a prompt will show asking for and input.
You can choose to use the `name` parameter as the `id` for the yml file, or give a different identifier.
* The `id` parameter *can* have spaces (' ') in it.
* If activated from content repository and no `outdir` given - A pack will be created in the "Packs" directory.
* If activated from content repo or within a pack directory and no `outdir` given -
An integration will be created in the "Integrations" directory and a script will be created in the "Scripts" repository.
* If no `outdir` given and the command is not activated from content repo nor a pack directory -
The pack/integration/script will be created in your current working directory.
* The templates are based on "Integrations/HelloWorld" and "Scripts/HelloWorldScript" found in content repo.

**Examples**
*Note: the bellow example explanations are given as though this command is activated from content repo directory.*

`demisto-sdk init`
This will prompt a message asking for a name for the pack, once given a pack will be created under the "Packs" directory.

`demisto-sdk init --integration -n MyNewIntegration -o path/to/my/dir`
This will create a new integration template named MyNewIntegration within "path/to/my/dir" directory.

`demisto-sdk init --script --id "My Script ID"`
This will prompt a message asking for a name for the script's directory and file name,
once given a script will be created under "Scripts" directory and the yml file will have the id "My Script ID".

`demisto-sdk init --pack -n My_Pack`
This will create a new pack named "My_Pack" under the "Packs" directory in content repo.
