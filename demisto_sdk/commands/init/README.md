## init
### Overview
Create a pack, integration or script template.


### Options
* **-n, --name**
The name given to the files and directories of new pack/integration/script being created.
* **--id**
The ID used for the integration/script YAML file.
* **-o, --output**
The output directory to which the created object will be saved. The default one is the current working directory.
* **--integration**
Create an integration.
* **--script**
Create a script.
* **--pack**
Create a pack and its subdirectories.
* **-t, --template**
Create an Integration/Script based on a specific template.</br>
Integration template options: HelloWorld, HelloIAMWorld, FeedHelloWorld.</br>
Script template options: HelloWorldScript
* **-a, --author_image** The path of author image will be presented in marketplace
under PUBLISHER section. File should be up to 4kb and in the dimensions of 120x50.
* **--demisto_mock**
Copy the demistomock. Relevant for initialization of Scripts and Integrations within a Pack.
* **--common-server**
Copy the CommonServerPython. Relevant for initialization of Scripts and Integrations within a Pack.
* **--xsiam**
Create an Event Collector based on a template, and create matching subdirectories.

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
* If a pack was created but no `author_image` was given - an empty 'Author_image.png' will be created at pack root
  directory. Later, when validating, user will be asked to add it manually.
* The default templates are based on "StarterPack/BaseIntegration" and "StarterPack/BaseScript" found in content repo.
* If `xsiam` and `integration` are set `output` is required.

**Examples**

*Note: the below example commands and explanations are given as though the command is activated from the content repo directory.*


`demisto-sdk init -n My_Pack`

Creates a new pack named "My_Pack" under the "Packs" directory in content repository.


`demisto-sdk init --integration -n MyNewIntegration -o path/to/my/dir`

Creates a new integration template named MyNewIntegration within "path/to/my/dir" directory.


`demisto-sdk init --script --id "My Script ID" -n MyScript`

Creates a named "MyScript" under the "Scripts" directory and the yml file will have the id "My Script ID".


`demisto-sdk init --pack -n My_Pack -a path/yourAuthorImage.png`

Creates a new pack named "My_Pack" under the "Packs" directory in content repo, and add an author image that
will be presented under PUBLISHER section in marketplace. Image file will be created under pack root directory.

`demisto-sdk init --pack -n My_Pack --xsiam`

Creates a new pack named "My_Pack" under the "Packs" directory in content repo, and add the relevant empty XSIAM directories under "My_Pack" directory.

`demisto-sdk init --integration -n MyNewIntegration -o path/Packs/My_Pack/Integration --xsiam`

Creates a new integration named MyNewIntegrationEventCollector within "path/Packs/My_Pack/Integration" directory,
In addition, this will create the relevant folders and files for parsing rules and modeling rules under My_Pack.
