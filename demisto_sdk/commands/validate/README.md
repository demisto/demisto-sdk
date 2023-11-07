## Validate

Makes sure your content repository files are in order and have valid file scheme.

**Use Cases**
This command is used to make sure that the content repo files are valid and are able to be processed by Demisto.
This is used in our validation process both locally and in Circle CI.

**Arguments**:
* **-g, --use-git**
Validate changes using git - this will check the current branch's changes against origin/master.
If the **--post-commit** flag is supplied: validation will run only on the current branch's changed files that have been committed.
If the **--post-commit** flag is not supplied: validation will run on all changed files in the current branch, both committed and not committed.
* **-a, --validate-all**
Whether to run all validation on all files or not.
* **-i, --input**
The path of the content pack/file to validate specifically.
* **-pc, --post-commit**
Whether the validation should run only on the current branch's committed changed files. This applies only when the **-g** flag is supplied.
* **-st, --staged**
Whether the validation should run only on the current branch's staged files. This applies only when the **-g** flag is supplied.
* **--prev-ver**
Previous branch or SHA1 commit to run checks against.
* **--no-multiprocessing**
Run validate all without multiprocessing, for debugging purposes.
* **-j, --json-file**
The JSON file path to which to output the command results.
* **--category-to-run**
Run specific validations by stating category they're listed under in the config file.
* **-f, --fix**
Wether to autofix failing validations with an available auto fix or not.
* **--config-path**
Path for a config file to run, if not given - will run the default path at: ...

**Examples**:

`demisto-sdk validate --prev-ver SHA1-HASH`
This will validate only changed files from the branch given (SHA1).

`demisto-sdk validate --post-commit`
This indicates that the command runs post commit.

`demisto-sdk validate -i Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml`
This will validate the file Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml only.

`demisto-sdk validate -a`
This will validate all files under `Packs` directory

`demisto-sdk validate -i Packs/HelloWorld`
This will validate all files under the content pack `HelloWorld`

### Notes
* In external repositories (repos which contain the `.private-repo-settings` file in its root) **all** the validations are ignorable.


### Error Codes and Ignoring Them
Each error found by validate  has an error code attached to it - the code can be found in brackets preceding the error itself.
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


Each user will have a personal config file which he can edit however he wants.
A default config file can be found [here](demisto_sdk/commands/validate/default_config.toml)
The config file will have few sections: validate_all, use_git, and sections provided by the user.
Each section will have the following options:
**select**: The validations to run.
**warning**: Validations to only throw warning (shouldn't fail the flow).
**ignorable_errors**: Validations that can be ignored using the pack-ignore.
If **category-to-run** is provided, the validations that will run will be according to the configuration in the particular section.

For example: if the following configurations are given
[custom_category]
select = ["BA101"]
then validate will run only BA101 validation.

In addition, each config file will have a **support_level** section which will be divided into xsoar, partner, and community each have ignore, select, warning, and ignorable_errors options. If the ignore-support-level flag is not given, the validations that will run will be according to both the given section (user custom section / use_git / validate_all) and the relevant support level.
For example: if the following configurations are given:
```buildoutcfg
[custom_category]
select = ["BA100", "BA101", "BA102"]
[support_level.community]
ignore = ["BA102"]
```
then validate will run all the validations with error codes "BA100", "BA101", "BA102" except for BA102 in case of community supported files

If you wish to ignore errors for a specific file in the pack insert the following to the `pack-ignore` file.
```buildoutcfg
[file:FILE_NAME]
ignore=BA101
```
