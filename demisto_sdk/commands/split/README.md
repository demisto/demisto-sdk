## split

### Overview
Splits downloaded scripts, integrations and generic module files into multiple files.
Integrations and scripts are split into the package format.
Generic modules have their dashboards split into separate files and modify the module to the content repository standard.

Files are stored in the content repository in a directory format, which enables performing extensive code validations and maintaining a more stable code base.
For more details [see](https://xsoar.pan.dev/docs/integrations/package-dir).

### Options
* **-i, --input**
The yml/json file to extract from.
* **-o, --output**
The output directory to write the extracted code/description/image/json to.
* **---no-demisto-mock**
Don't add an import for demisto mock (only for yml files).
* **--no-common-server**
Don't add an import for CommonServerPython or CommonServerPowerShell (only for yml files).
* **--no-auto-create-dir**
Don't auto create the directory if the target directory ends with
*Integrations/*Scripts/*GenericModules/*Dashboards. The auto directory created will be named according to the
Integration/Script name.
* **--new-module-file**
Create a new module file instead of editing the existing file (only for json files).

**Examples**
1. `demisto-sdk split -i Integrations/integration-MyInt.yml -o Integrations/MyInt`
Splits the yml file to a directory with the integration components (code, image, description, pipfile etc.)

2. `demisto-sdk split -i Scripts/script-MyInt.yml -o Scripts/MyInt`
Splits the yml file to a directory with the script components (code, description, pipfile etc.)

3. `demisto-sdk split -i Integrations/integration-powershell_ssh_remote.yml -o Packs/PowerShellRemoting/Integrations/`
Splits a PowerShell integration. Output is specifying just the `Integrations` dir, thus the target dir will be auto created.

4. `demisto-sdk split -i Packs/ThreatIntel/GenericModules/genericmodule-ThreatIntel.json`
Extracts the Dashboards found in the Generic Module found in `Packs/ThreatIntel/GenericModules/genericmodule-ThreatIntel.json` .
If you are running in the `content` repository the dashboards will be extracted to the relevant directory in the pack: `Packs/ThreatIntel/Dashboards`
Otherwise the dashboards will be created in your current working directory.
The Generic Module will also be edited to fit content standard.

5. `demisto-sdk split -i Packs/ThreatIntel/GenericModules/genericmodule-ThreatIntel.json -o Packs/ThreatIntel --new-module-file`
Extracts the Dashboards found in the Generic Module found in `Packs/ThreatIntel/GenericModules/genericmodule-ThreatIntel.json` as well as create a
new module file without changing the original file. All the new files will be created in `Packs/ThreatIntel`.
