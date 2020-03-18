## Unify

Unify the code, image and description files to a single Demisto yaml file.

**Use Cases**:
This command is used in order to create a unified yml file, able to be uploaded to Demisto via the
"Upload Integration" or "Upload Script" buttons, in Demisto's Settings and Automation tabs respectively.

**Arguments**:
* **-i, --input**
  The path to the directory in which the files reside
* **-o, --output**
  The path to the directory into which to write the unified yml file

**Examples**:
`demisto-sdk unify -i Integrations/MyInt -o Integrations`
This will grab the integration components in "Integrations/MyInt" directory and unify them to a single yaml file
that will be created in the "Integrations" directory.
<br/><br/>

`demisto-sdk unify -i Scripts/MyScr -o Scripts`
This will grab the script components in "Scripts/MyScr" directory and unify them to a single yaml file
that will be created in the "Scripts" directory.
