## Validate

Makes sure your content repository files are in order and have valid yml file scheme.

**Notes**

In order to run the README validator:
- Node should be installed on you machine
- The modules '@mdx-js/mdx', 'fs-extra', 'commander' should be installed in node-modules folder.
    If not installed, the validator will print a warning with the relevant module that is missing.
    please install it using "npm install *missing_module_name*"
- 'DEMISTO_README_VALIDATION' environment variable should be set to True.
    To set the environment variables, run the following shell commands:
    export DEMISTO_README_VALIDATION=True

In case of a private repo and an un-configured 'DEMISTO_SDK_GITHUB_TOKEN' or 'DEMISTO_SDK_GITLAB_TOKEN' validation of version bumps in files will be done with the local remote git branch.

**Use Cases**
This command is used to make sure that the content repo files are valid and are able to be processed by Demisto.
This is used in our validation process both locally and in Circle CI.

**Arguments**:
* **--no-backward-comp**
Whether to check backward compatibility or not.
* **--no-conf-json**
Skip conf.json validation.
* **-s, --id-set**
Perform validations using the id_set file.
* **-idp, --id-set-path**
The path of the id-set.json used for validations.
* **--prev-ver**
Previous branch or SHA1 commit to run checks against.
* **-g, --use-git**
Validate changes using git - this will check the current branch's changes against origin/master.
If the **--post-commit** flag is supplied: validation will run only on the current branch's changed files that have been committed.
If the **--post-commit** flag is not supplied: validation will run on all changed files in the current branch, both committed and not committed.
* **-pc, --post-commit**
Whether the validation should run only on the current branch's committed changed files. This applies only when the **-g** flag is supplied.
* **-st, --staged**
Whether the validation should run only on the current branch's staged files. This applies only when the **-g** flag is supplied.
* **-iu, --include-untracked**
Whether to include untracked files in the validation. This applies only when the **-g** flag is supplied.
* **-i, --input**
Path of file to validate specifically.
* **-a, --validate-all**
Whether to run all validation on all files or not.
* **-i, --input**
The path of the content pack/file to validate specifically.
* **---skip-pack-release-notes**
Validation will not not be performed using the updated pack release notes format.
* **--print-ignored-errors**
Whether to print ignored errors as warnings.
* **--print-ignored-files**
Print which files were ignored by the command.
* **--no-docker-checks**
Whether to run docker image validation.
* **--silence-init-prints**
Whether to skip the initialization prints.
* **--skip-pack-dependencies**
Skip validation of pack dependencies.
* **--create-id-set**
Whether to create the id_set.json file.
* **-j, --json-file**
The JSON file path to which to output the command results.
* **--skip-schema-check**
Whether to skip the file schema check.
* **--debug-git**
Whether to print debug logs for git statuses.
* **--print-pykwalify**
Whether to print the pykwalify log errors.
* **--quiet-bc-validation**
Set backwards compatibility validation's errors as warnings.
* **--allow-skipped**
Don't fail on skipped integrations or when all test playbooks are skipped.
* **-sv, --run-specific-validations**
Validate only specific validations by error codes.
* **--graph**
Whether use the content graph

**Examples**:
`demisto-sdk validate -g --no-backwards-comp`
This will validate only changed files from content origin/master branch and will exclude backwards
compatibility checks.
<br><br>

`demisto-sdk validate -j`
This will validate all content repo files and including conf.json file.
<br><br>

`demisto-sdk validate --prev-ver SHA1-HASH`
This will validate only changed files from the branch given (SHA1).
<br><br>

`demisto-sdk validate --post-commit`
This indicates that the command runs post commit.
<br><br>

`demisto-sdk validate -i Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml`
This will validate the file Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml only.
<br><br>

`demisto-sdk validate -a`
This will validate all files under `Packs` directory
<br><br>

`demisto-sdk validate -i Packs/HelloWorld`
This will validate all files under the content pack `HelloWorld`
<br><br>

`demisto-sdk validate -i Packs/HelloWorld --run-specific-validations BA101`
This will validate all files under the content pack `HelloWorld` using only the validation corresponds to the error code BA101.
<br><br>

`demisto-sdk validate -i Packs/HelloWorld --run-specific-validations BA`
This will validate all files under the content pack `HelloWorld` using only the validations from error type of BA.
<br><br>

### Error Codes and Ignoring Them
Starting in version 1.0.9 of Demisto-SDK, each error found by validate (excluding `pykwalify` errors) has an error
code attached to it - the code can be found in brackets preceding the error itself.
For example: `path/to/file: [IN103] - The type field of the proxy parameter should be 8`

The first 2 letters indicate the error type and can be used to easily identify the cause of the error.
| Code | Type |
| --- | --- |
| BA | Basic error |
| BC | Backwards compatibility error |
| CJ | Conf json error |
| CL | Classifier error |
| DA | Dashboard error |
| DB | DBootScore error |
| DO | Docker error |
| DS | Description error |
| ID | Id set error |
| IF | Incident field or type error |
| IM | Image error |
| IN | Integration or script error |
| IT | Incident type error |
| MA | Mapper error |
| PA | Pack files error (pack-metadata, pack-secrets, pack-ignore) |
| PB | Playbook error |
| RM | Readme error |
| RN | Release notes error |
| RP | Reputation error |
| SC | Script error |
| ST | Structure error |
| WD | Widget error |


If you wish to ignore errors for a specific file in the pack insert the following to the `pack-ignore` file.
```buildoutcfg
[file:FILE_NAME]
ignore=BA101
```

*Note*: Currently only `BA101` is ignorable.
