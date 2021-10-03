## split
Split a XSOAR downloaded Scripts, Integrations and Generic Module files and split it into multiple files.
Integration and Scripts will be in split into the package format - https://xsoar.pan.dev/docs/integrations/package-dir
Generic Modules will have their Dashboards split into separate files and will modify the module to content repo standard.

**Use-Cases**
Our work in the Content repository is done in a directory format, which enables us to preform more validations on our
code.
In turn those validation help us maintain a more stable code base. For more details about [see](https://xsoar.pan.dev/docs/integrations/package-dir).

**Arguments**:
* **-i, --input**
The yml/json file to extract from.
* **-o, --output**
The output dir to write the extracted code/description/image/json to.
* **---no-demisto-mock**
Don't add an import for demisto mock (only for yml files)
* **--no-common-server**
Don't add an import for CommonServerPython or CommonServerPowerShell (only for yml files)
* **--no-auto-create-dir**
Don't auto create the directory if the target directory ends with
*Integrations/*Scripts/*GenericModules/*Dashboards. The auto directory created will be named according to the
Integration/Script name.
* **--no-pipenv**
Don't auto create pipenv for requirements installation. (only for yml files)
* **--new-module-file**
Create a new module file instead of editing the existing file. (only for json files)

**Examples**
1. `demisto-sdk split -i Integrations/integration-MyInt.yml -o Integrations/MyInt`
This will split the yml file to a directory with the integration components (code, image, description, pipfile etc.)

2. `demisto-sdk split -i Scripts/script-MyInt.yml -o Scripts/MyInt`
This will split the yml file to a directory with the script components (code, description, pipfile etc.)

3. `demisto-sdk split -i Integrations/integration-powershell_ssh_remote.yml -o Packs/PowerShellRemoting/Integrations/`
Split a PowerShell integration. Output is specifying just the `Integrations` dir, thus the target dir will be auto created.

4. `demisto-sdk split -i Packs/ThreatIntel/GenericModules/genericmodule-ThreatIntel.json`
Extract the Dashboards found in the Generic Module found in `Packs/ThreatIntel/GenericModules/genericmodule-ThreatIntel.json` .
If you are running in the `content` repository the dashboards will be extracted to the relevant directory in the pack: `Packs/ThreatIntel/Dashboards`
Otherwise the dashboards will be created in your current working directory.
The Generic Module will also be edited to fit content standard.

5. `demisto-sdk split -i Packs/ThreatIntel/GenericModules/genericmodule-ThreatIntel.json -o Packs/ThreatIntel --new-module-file`
Extract the Dashboards found in the Generic Module found in `Packs/ThreatIntel/GenericModules/genericmodule-ThreatIntel.json` as well as create a
new module file without changing the original file. All the new files will be created in `Packs/ThreatIntel`.
