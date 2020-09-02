## init
Create a pack, integration or script template _or_ create a pack from a contribution ZIP file.

**Use-Cases**
* This command is used to ease the initial creation of a pack, integration or a script.
* Create a pack from a contribution ZIP file downloaded from the Cortex XSOAR marketplace.

**Arguments**:
* **-n, --name** The name given to the files and directories of new pack/integration/script being created
* **--id** The id used for the yml file of the integration/script
* **-o, --output** The output directory to which the created object will be saved
* **--integration** Create an integration
* **--script** Create a script
* **--pack** Create a pack
* **-c, --contribution** The path to the contribution zip file to convert to a pack in the content repo
* **-d, --description** The description to attach to the pack created from a contribution zip file
* **--author** The author to attach to the pack created from a contribution zip file

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
* The templates are based on "Integrations/HelloWorld" and "Scripts/HelloWorldScript" found in content repo.
* If the `contribution` parameter is passed, all additional parameters other than `name`, `description` and `author`
will be ignored.
* When creating a pack from a contribution zip file, the `email` field in the pack's `pack_metadata.json` file will
be left empty _even_ if the zip file's metadata file included an email address.
* When creating a pack from a contribution zip file, the `support` field in the pack's `pack_metadata.json` file will
be set to `community`.
* When passing the `contribution` parameter, the command should be executed from within the content repository,
otherwise the command will fail.

**Examples**

*Note: the below example commands and explanations are given as though the command is activated from the content repo directory.*


`demisto-sdk init`

This will prompt a message asking for a name for the pack, once given a pack will be created under the "Packs" directory.


`demisto-sdk init --integration -n MyNewIntegration -o path/to/my/dir`

This will create a new integration template named MyNewIntegration within "path/to/my/dir" directory.


`demisto-sdk init --script --id "My Script ID"`

This will prompt a message asking for a name for the script's directory and file name,
once given a script will be created under "Scripts" directory and the yml file will have the id "My Script ID".


`demisto-sdk init --pack -n My_Pack`

This will create a new pack named "My_Pack" under the "Packs" directory in content repo.


`demisto-sdk init --contribution ~/Downloads/my_contribution.zip`

This will use the data and content items in the zip file "my_contribution.zip" to construct a pack in the "Packs"
directory in the content repo which will contain the content items from the zip file formatted to the content repo's
conventions and expected file and directory structure.


`demisto-sdk init -n "My New Pack" -c ~/Downloads/my_contribution.zip -d "This pack introduces the 'My Example' Integration allowing you to execute commands on 'My Example' product directly from Cortex XSOAR" --author "Octocat Smith"`

This will do the same as in the previous example except that it will use the passed name, description and author
for the converted contribution pack metadata.
