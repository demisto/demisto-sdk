
## create-content-artifacts
Create content artifacts.

**Use-Cases**:
This command is primarily intended for internal use. During our CI/CD build process, this command creates archive files containing integrations, scripts and playbooks which are deployed to demisto instances for testing. The `content_new.zip`, `content_test.zip`, and `content_packs.zip` files are created and moved to the directory passed as an argument to the command (in a circleci build, this should be the path to the artifacts directory). In addition to creating the content archive files, this command tries to copy the `id_set.json` and `release_notes.md` files to the artifacts directory (which is passed as a command argument). The user can pass the `-p` flag to the command. This will preserve the intermediate directories created in the process of creating the content archive files (which would be useful if there is a need to inspect the files and debug).

**Arguments**:
* **-a ARTIFACTS_PATH, --artifacts_path ARTIFACTS_PATH**
The path of the directory in which you want to save the created content artifacts
* *-p, --preserve_bundles*
Flag for if you'd like to keep the bundles created in the process of making the content artifacts

**Examples**:
`demisto-sdk create -a .`
This will create content artifacts in the current directory.
