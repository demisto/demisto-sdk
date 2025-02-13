## Update Release Notes

### Overview

Automatically generates release notes for a given pack and updates the `pack_metadata.json` version for changed items.

This command creates a new release notes file under the ReleaseNotes directory in the given pack in the form of X_Y_Z.md where X_Y_Z is the new pack version. The command automatically bumps the `currentVersion` found in the `pack_metadata.json` file. After running this command, add the newly created release notes file to GitHub and add your notes under their respective headlines.

For a private repository and an unconfigured DEMISTO_SDK_GITHUB_TOKEN, remote files are fetched from the remote branch of the local repo.

### Options
* **-i, --input**

    The pack name or relative path of the content pack you wish to generate release notes for. For example, 'Packs/Pack_Name'.

* **-u, --update-type**

    Optional. If no update_type is defined, the `currentVersion` will be bumped as a revision.

    The type of update being done. Available options are:
    - major
    - minor
    - revision
    - documentation (revision)

* **-g, --use-git**

    Use git to identify the relevant changed files, will be used by default if '-i' is not set

* **-f, --force**

    Update the release notes of a pack even if no changes that require update were made.

* **--text**

    Text to add to all the release notes files.

* **--pre_release**

    Indicates that this update is for a pre-release version. The `currentVersion` will change to reflect the pre-release version number.

* **--prev-ver**

    Previous branch or SHA1 commit to run checks against.

* **-v, --version**

    Bump to a specific version. Cannot be used with `-u, --update_type` flag.

* **-bc, --breaking-changes**

    If new version contains breaking changes.


### Examples
```
demisto-sdk update-release-notes -i Packs/HelloWorld -u minor
```
Creates a new markdown file in the `ReleaseNotes` folder for the HelloWorld pack and bump the `currentVersion` with a **minor** increment.
<br/><br/>
```
demisto-sdk update-release-notes -i Packs/HelloWorld -u major
```
Creates a new markdown file in the `ReleaseNotes` folder for the HelloWorld pack and bump the `currentVersion` with a **major** increment.
<br/><br/>
```
demisto-sdk update-release-notes -i Packs/HelloWorld -u revision
```
Creates a new markdown file in the `ReleaseNotes` folder for the HelloWorld pack and bump the `currentVersion` with a **revision** increment.
<br/><br/>
```
demisto-sdk update-release-notes -g -u revision
```
Creates a new markdown file in the `ReleaseNotes` folder for **all** changed packs and bump the `currentVersion` for **all** changed packs with a **revision** increment.
<br/><br/>

```
demisto-sdk update-release-notes -i Packs/HelloWorld -u revision --pre_release
```
Creates a new markdown file in the `ReleaseNotes` folder for the HellWorld pack and bump the `currentVersion` with a **revision** increment as well as append `pre_release` to the `currentVersion`.
