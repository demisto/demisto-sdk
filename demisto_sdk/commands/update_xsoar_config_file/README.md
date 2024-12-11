## update-xsoar-config-file

### Overview

Handle your XSOAR Configuration File.

**Use Cases**:
- Add automatically all the installed MarketPlace Packs to the marketplace_packs section in XSOAR Configuration File.
- Add a Pack to the marketplace_packs section in the Configuration File.
- Add a Pack to the custom_packs section in the Configuration File.

### Options:
* **-pi, --pack-id**
  The Pack ID to add to XSOAR Configuration File.
* **-pd, --pack-data**
  The Pack data to add to XSOAR Configuration File. Pack URL for Custom Pack and Pack Version for OOTB Pack.
* **-mp, --add-marketplace-pack**
  Add a Pack to the marketplace_packs section in the Configuration File.
* **-cp, --add-custom-pack**
  Add a Pack to the custom_packs section in the Configuration File.
* **-all, --add-all-marketplace-packs**
  Add all packs currently installed on the marketplace to the marketplace_packs section in XSOAR Configuration File.
* **--insecure**
  Skip certificate validation.
* **--file-path**
  The XSOAR Configuration File path in your Repository, the default value is in the repo level.

**Examples**:
`demisto-sdk update-xsoar-config-file --add-all-marketplace-packs`
This will downloads all the installed MarketPlace Packs to the marketplace_packs section in XSOAR Configuration File.

`demisto-sdk update-xsoar-config-file --add-marketplace-pack --pack-id PackId --pack-data 1.0.1`
This will add PackId with 1.0.1 version to the marketplace_packs section in XSOAR Configuration File.

`demisto-sdk update-xsoar-config-file --add-custom-pack --pack-id PackId --pack-data Packs/PackID`
This will add PackId with Packs/PackId URL to the custom_packs section in XSOAR Configuration File.
