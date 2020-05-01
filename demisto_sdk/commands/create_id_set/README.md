## create-id-set
Create the content dependency tree by ids.

**Use-Cases**:
This command is primarily intended for internal use. During our CI/CD build process, this command creates a dependency tree containing integrations, scripts and playbooks. The `id_set.json` file is created with the outputs.

**Arguments**:
* **-o OUTPUT, --output OUTPUT**
The path of the file in which you want to save the created id set.

**Examples**:
`demisto-sdk create-id-set -o Tests/id_set.json`
This will create the id set in the file Tests/id_set.json.
