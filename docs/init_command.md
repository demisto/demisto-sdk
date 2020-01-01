## init
Create a pack, integration or script template. If `--integration` and `--script` flags are not given the command will create a pack.

* **-n, --name** The name given to the new pack/integration/script being created
* **-o, --outdir** The directory to which the created object will be saved.
* **--integration** Create an integration
* **--script** Create a script

**Notes**
* If a `name` will not be given, a prompt will show asking for an input -
A pack, integration or script can not be created without a given name.
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

`demisto-sdk init --script`
This will prompt a message asking for a name for the script, once given a script will be created under "Scripts" directory.
