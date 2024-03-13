## Validate

Makes sure your content repository files are in order and have valid file scheme.

**Use Cases**
This command is used to make sure that the content repo files are valid and are able to be processed by the platform.
This is used in our validation process both locally and in gitlab.

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
Path for a config file to run, if not given - will run the default path at: [demisto_sdk/commands/validate/default_config.toml](default_config.toml)
* **--ignore-support-level**
Wether to skip validations based on their support level or not.
* **--run-old-validate**
Wether to skip the old validate flow.
* **--skip-new-validate**
Wether to run the new validate flow.

**Examples**:

`demisto-sdk validate --prev-ver SHA1-HASH`
This will validate only changed files from the branch given (SHA1).

`demisto-sdk validate --post-commit`
This indicates that the command runs post commit.

`demisto-sdk validate -i Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml`
This will validate the file Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml only.

`demisto-sdk validate -a`
This will validate all files under `Packs` directory.

`demisto-sdk validate -i Packs/HelloWorld`
This will validate all files under the content pack `HelloWorld`.

`demisto-sdk validate --run-old-validate --skip-new-validate -a`
This will validate all files in the repo using the old validate method.

`demisto-sdk validate --config-path {config_file_path} -a`
This will validate all files in the repo using the settings configured in the config file in the given path.

### Error Codes and Ignoring Them
Each error found by validate  has an error code attached to it - the code can be found in brackets preceding the error itself.
For example: `path/to/file: [IN103] - The type field of the proxy parameter should be 8`
In addition, each pack has a `.pack-ignore` file. In order to ignore a certain validation for a given file, the error-code needs to be listed in the **ignorable_errors** section in the config-file (more about this in the config file section), and the user need to mention the file name (only the name and extension, without the whole path), and the error code to ignore.
For example: This .pack-ignore will not fail ipinfo_v2.yml on the validations with the codes BA108 & BA109.
[file:ipinfo_v2.yml]
ignore=BA108,BA109

### Config file
Each user will have a personal config file which he can edit however he wants.
A default config file can be found [here.](default_config.toml)
The default config file cover all the mandatory validations - the validations that without them te upload will fail.
The config file will have few sections:
**ignorable_errors** - A list of the error codes that can be ignored in the .pack-ignore file.
, validate_all, use_git, and custom sections provided by the user.
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
