
## create-content-artifacts
Create content artifacts.

**Use-Cases**:\
Generating the following artifacts:
   1. content_new - Contains all content objects of type json,yaml (from_version < 6.0.0), Used for bi-weekly content Releases.
   2. content_test - Contains all test scripts/playbooks (from_version < 6.0.0), Used for CircleCI tests.
   3. content_all - Contains all files from content_new and content_test (from_version < 6.0.0), Used for CircleCI tests.
   4. content_packs - Contains all packs from Packs - Ignoring internal files (to_version >= 6.0.0), Used for building MarketPlace packs.


**Arguments**:
* **-a ARTIFACTS_PATH, --artifacts_path ARTIFACTS_PATH**
Destination directory to create the artifacts.
* **--zip/--no-zip**
Zip content artifacts folders.
* **-v RELEASE_VERSION, --content_version RELEASE_VERSION**
The content version in CommonServerPython.
* **-s FILES_SUFFIX, --suffix FILES_SUFFIX**
Suffix to add all yaml/json/yml files in the created artifacts.
* **--cpu CPUS_NUMBER**
Number of cpus/vcpus availble - only required when os not reflect number of cpus
> CircleCI allways show 32, but for example medium has 3.

**Examples**:
1. create artifacts without zipping the folders - `demisto-sdk create-content-artifacts -a DEST --no-zip`
2. create artifacts while zipping the folders - `demisto-sdk create-content-artifacts -a DEST`
