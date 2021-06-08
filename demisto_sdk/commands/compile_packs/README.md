## compile-packs

compile content packs to uploadable zip file.

**Use Cases**:
This command is used in order to create a zip file, able to be uploaded to Demisto via the
"Upload pack" button in Demisto's marketplace or directly with the -u flag in this command.

**Arguments**:
* **-i, --input**
  The packs to create artifacts for. Optional values are: `all` or csv list of pack names.
* **-o, --output**
  The path to the directory into which to write the zip files
* **-v RELEASE_VERSION, --content_version RELEASE_VERSION**
  The content version in CommonServerPython.
* **-u, --upload**
  Upload the compiled packs to the marketplace.
* **---zip_all**
  Zip all the packs in one zip file.

**Examples**:
`demisto-sdk compile-packs -i Campaign -o "DestinationDir"`
This will compile the "Campaign" pack into Campaign.zip file in the "DestinationDir" directory.
<br/><br/>

`demisto-sdk compile-packs -i Campaign -o "DestinationDir" -u`
This will compile the "Campaign" pack into Campaign.zip file in the "DestinationDir" directory
and will upload the created Campaign.zip to the marketplace.
