## split-yml
Split a Demisto downloaded yml file (of an integration or a script) and split it into multiple files so it will be in
the package format - https://xsoar.pan.dev/docs/integrations/package-dir

**Use-Cases**
Our work in the Content repository is done in a directory format, which enables us to preform more validations on our
code.
In turn those validation help us maintain a more stable code base. For more details about [see](https://xsoar.pan.dev/docs/integrations/package-dir).

**Arguments**:
* **-i, --input**
The yml file to extract from
* **-o, --output**
The output dir to write the extracted code/description/image to
* **---no-demisto-mock**
Don't add an import for demisto mock
* **--no-common-server**
Don't add an import for CommonServerPython or CommonServerPowerShell
* **--no-auto-create-dir**
Don't auto create the directory if the target directory ends with
*Integrations/*Scripts. The auto directory created will be named according to the
Integration/Script name.
* **--no-pipenv**
Don't auto create pipenv for requirements installation.

**Examples**
1. `demisto-sdk split-yml -i Integrations/integration-MyInt.yml -o Integrations/MyInt`
This will split the yml file to a directory with the integration components (code, image, description, pipfile etc.)

2. `demisto-sdk split-yml -i Scripts/script-MyInt.yml -o Scripts/MyInt`
This will split the yml file to a directory with the script components (code, description, pipfile etc.)

3. `demisto-sdk split-yml -i Integrations/integration-powershell_ssh_remote.yml -o Packs/PowerShellRemoting/Integrations/`
Split a PowerShell integration. Output is specifying just the `Integrations` dir, thus the target dir will be auto created.
