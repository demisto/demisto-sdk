
## create-content-artifacts
Create content artifacts.

**Use-Cases**:\
Generating the following artifacts:
   1. content_new - Contains all content objects of type json,yaml (from_version < 6.0.0), Used for bi-weekly content Releases.
   2. content_test - Contains all test scripts/playbooks (from_version < 6.0.0), Used for CircleCI tests.
   3. content_all - Contains all files from content_new and content_test (from_version < 6.0.0), Used for CircleCI tests.
   4. content_packs - Contains all packs from Packs - Ignoring internal files (to_version >= 6.0.0), Used for building MarketPlace packs.
   5. uploadable_packs - Contains zipped packs that are ready to be uploaded to Cortex XSOAR machine (under some conditions).

**Arguments**:
* **-a --artifacts_path**
Destination directory to create the artifacts.
* **--zip/--no-zip**
Zip content artifacts folders.
* **--packs**
Create only content_packs artifacts. Used for server version 5.5.0 and lower.
* **-v --content_version**
The content version in CommonServerPython.
* **-s --suffix** The suffix to add all yaml/json/yml files in the created artifacts.
* **--cpus**
Number of cpus/vcpus availble - only required when os not reflect number of cpus
> CircleCI always show 32, but for example medium has 3.
* **-idp --id_set_path**
The full path of id_set.json.
* **-p --pack-names**
Packs to create artifacts for. Optional values are: `all` or csv list of packs. Default is set to `all`.
* **-sd --sign-directory**
Path to the signDirectory executable file.
* **-sk --signature-key**
Base64 encoded signature key used for signing packs.
* **-rt, --remove-test-playbooks**
Should remove test playbooks from content packs or not.

**Examples**:
1. create artifacts without zipping the folders - `demisto-sdk create-content-artifacts -a DEST --no-zip`
2. create artifacts while zipping the folders - `demisto-sdk create-content-artifacts -a DEST`
3. create artifacts for specific packs - `demisto-sdk create-content-artifacts -a DEST -p Base,AutoFocus`
