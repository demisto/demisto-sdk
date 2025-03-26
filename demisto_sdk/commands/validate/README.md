## Validate

### Overview

This command ensures that the content repository files are valid and are able to be processed by the platform.
This is used in our validation process both locally and in Gitlab.

### Options
* **-g, --use-git**
Validate changes using Git - this will check the current branch's changes against origin/master.
If the **--post-commit** flag is supplied: validation will run only on the current branch's changed files that have been committed.
If the **--post-commit** flag is not supplied: validation will run on all changed files in the current branch, both committed and not committed.
Note that the validations being executed might differ according to the [validations configured for this execution mode](#Validation-Config-file).
* **-a, --validate-all**
Whether to run all validation on all files or not.
Note that the validations being executed might differ according to the [validations configured for this execution mode](#Validation-Config-file).
* **-i, --input**
The path of the content pack/file to validate specifically.
Note that the validations being executed might differ according to the [validations configured for this execution mode](#Validation-Config-file).
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
Run specific validations by stating the category they're listed under in the config file.
* **-f, --fix**
Whether to auto fix failing validations with an available auto.
* **--config-path**
Path for a config file to run. If not given - will run the default path at: [demisto_sdk/commands/validate/default_config.toml](default_config.toml)
* **--ignore-support-level**
Whether to skip validations based on their support level or not.
* **--run-old-validate**
Whether to run the old validate flow or not. Alternatively, you can configure the RUN_OLD_VALIDATE env variable
* **--skip-new-validate**
Whether to skip the new validate flow or not. Alternatively, you can configure the SKIP_NEW_VALIDATE env variable.
* **-sv, --run-specific-validations**
A comma separated list of validations to run stated the error codes.
* **--ignore**
An error code to not run. To ignore more than one error, repeat this option (e.g. `--ignore AA123 --ignore BC321`)

### Validation Error Codes
Each error found by validate has an error code attached to it. The code can be found in brackets preceding the error itself.  
For example: `path/to/file: [IN103] - The type field of the proxy parameter should be 8`
In addition, each pack has a `.pack-ignore` file. In order to ignore a certain validation for a given file, the error-code needs to be listed in the **ignorable_errors** section in the config-file (see the [Config file section](#config-file)), and the user needs to mention the file name (only the name and extension, without the whole path), and the error code to ignore.
For example: This .pack-ignore will not fail ipinfo_v2.yml on the validations with the codes BA108 & BA109.
[file:ipinfo_v2.yml]
ignore=BA108,BA109

### Validation Config file
You can define a config file to suit your business needs. If no file is defined, the  [default config file](default_config.toml) will be used.
The default configuration covers basic validations, which prevents unsuccessful uploads of the validated content to Cortex XSOAR.
#### How to define a configuration file
You can define the following sections:
**ignorable_errors** - a list of the error codes that can be ignored for individual content items in the .pack-ignore file.
**path_based_validations** - the configurations to run when running with -a / -i flags.
**use_git** - the configurations to run when running with -g flag.
You can also define custom sections - which can be configured to run with the **category-to-run** flag.
Two example custom categories are given with the default config file:
**xsoar_best_practices_use_git** - our recommended set of validations to run when running with -g, may be modified from time to time.
**xsoar_best_practices_path_based_validations** - our recommended set of validations to run when running with -a / -i, may be modified from time to time.
Each section will have the following options:
**select** - The validations to run.
**warning** - Validations for which to only throw warnings (will not fail the flow).
The config file can also configure which validations to ignore based on the content item support level using the section header support_level.<support_type> where support_type is one of  xsoar, partner, or community.
If the user wishes to ignore this feature in some of the calls, he can use the **--ignore-support-level** flag.

**Examples**:
```
[custom_category]
select = ["BA101"]
```
Validate will run only BA101 validation.

```
[custom_category]
select = ["BA100", "BA101", "BA102"]
[support_level.community]
ignore = ["BA102"]
```
Validate will run all the validations with error codes "BA100", "BA101", "BA102" except for BA102 in case of community supported files.

### Examples:

`demisto-sdk validate --prev-ver SHA1-HASH`
Validates only changed files from the branch (for SHA1 hash files).

`demisto-sdk validate --post-commit`
Runs a post commit.

`demisto-sdk validate -i Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml`
validates only the Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml file.

`demisto-sdk validate -a`
Validates all files under the `Packs` directory.

`demisto-sdk validate -i Packs/HelloWorld`
Validates all files under the `HelloWorld` content pack.

`demisto-sdk validate --run-old-validate --skip-new-validate -a`
This will validate all files in the repo using the old validate method.

`demisto-sdk validate --config-path {config_file_path} -a`
TValidates all files in the repository using the settings configured in the config file in the given path.
