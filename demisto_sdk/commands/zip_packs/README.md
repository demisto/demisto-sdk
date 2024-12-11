## zip-packs

### Overview

Creates a zip file that can be uploaded to Cortex XSOAR via the Upload pack button in the Cortex XSOAR Marketplace or directly with the -u flag in this command.

### Options
* **-i, --input**
  The packs to create artifacts for. Optional values are: `all` or csv list of pack names.
* **-o, --output**
  The path to the directory into which to write the zip files.
* **-v --content-version**
  The content version in CommonServerPython.
* **-u, --upload**
  Upload the unified packs to the marketplace.
* **--zip-all**
  Zip all the packs in one zip file.

**Examples**:
`demisto-sdk zip-packs -i Campaign -o "DestinationDir"`
Zips the "Campaign" pack into Campaign.zip file in the "DestinationDir" directory.

`demisto-sdk zip-packs -i Campaign -o "DestinationDir" -u`
Zips the "Campaign" pack into uploadable_packs.zip file in the "DestinationDir" directory
and will upload the created uploadable_packs.zip to the marketplace.
