## Update Release Notes

**Automatically identify and create a release notes template for changed items.**

### Use Cases
This command is used in order to create or update release notes for a new pack version. The command will also automatically bump the `currentVersion` found in the `pack_metadata.json` file.

In case of a private repo and an un-configured 'DEMISTO_SDK_GITHUB_TOKEN' remote files will be fetched from the remote branch of the local repo.

### Arguments
* **-i, --input <PACK_PATH>**

    The path of the content pack you wish to generate release notes for.

* **-u, --update-type**

    Optional. If no update_type is defined, the `currentVersion` will be bumped as a revision.

    The type of update being done. Available options are:
    - major
    - minor
    - revision
    - maintenance (revision)
    - documentation (revision)

* **-g, --use-git**

    Uses git to identify the relevant changed files and updates all release notes in every pack which has been changed.
    Will be used by default if '-i' is not set. Please note that the `-u` argument will be applied to **all** changed packs.

* **-f, --force**

    Update the release notes of a pack even if no changes that require update were made.

* **--text**

    Text to add to all of the release notes files.

* **--pre_release**

    Indicates that this update is for a pre-release version. The `currentVersion` will change to reflect the pre-release version number.

* **--prev-ver**

    Previous branch or SHA1 commit to run checks against.

* **-v, --version <DESIRED_VERSION>**

    Bump to a specific version. Cannot be used with `-u, --update_type` flags.

* **-idp, --id-set-path**

    The path of the id-set.json used for APIModule updates.

### Examples
```
demisto-sdk update-release-notes -i Packs/HelloWorld -u minor
```
This will create a new markdown file in the `ReleaseNotes` folder for the HelloWorld pack and bump the `currentVersion` with a **minor** increment.
<br/><br/>
```
demisto-sdk update-release-notes -i Packs/HelloWorld -u major
```
This will create a new markdown file in the `ReleaseNotes` folder for the HelloWorld pack and bump the `currentVersion` with a **major** increment.
<br/><br/>
```
demisto-sdk update-release-notes -i Packs/HelloWorld -u revision
```
This will create a new markdown file in the `ReleaseNotes` folder for the HelloWorld pack and bump the `currentVersion` with a **revision** increment.
<br/><br/>
```
demisto-sdk update-release-notes -g -u revision
```
This will create a new markdown file in the `ReleaseNotes` folder for **all** changed packs and bump the `currentVersion` for **all** changed packs with a **revision** increment.
<br/><br/>

```
demisto-sdk update-release-notes -i Packs/HelloWorld -u revision --pre_release
```
This will create a new markdown file in the `ReleaseNotes` folder for the HellWorld pack and bump the `currentVersion` with a **revision** increment as well as append `pre_release` to the `currentVersion`.
