# Changelog

[PyPI History][1]

[1]: https://pypi.org/project/demisto-sdk/#history
### 0.4.6
* Fixed an issue where the *validate* command did not identify CHANGELOG in packs.
* Added a new command, *id-set* to create the id set - the content dependency tree by file IDs.

### 0.4.5
* generate-docs command:
    * Added the *use_cases*, *permissions*, *command_permissions* and *limitations*.
    * Added the *--insecure* argument to support running the script and integration command in Demisto.
    * Removed the *-t yml_type* argument, the file type will be inferred.
    * The *-o --output* argument is no longer mandatory, default value will be the input file directory.
* Added support for env var: *DEMISTO_SDK_SKIP_VERSION_CHECK*. When set version checks are skipped.
* Fixed an issue in which the CHANGELOG files did not match our scheme.
* Added a validator to verify that there are no hidden integration parameters.
* Fixed an issue where the *validate* command ran on test files.
* Removed the *env-dir* argument from the demisto-sdk.
* README files which are html files will now be skipped in the *validate* command.
* Added support for env var: *DEMISTO_README_VALIDATOR*. When not set the readme validation will not run.

### 0.4.4
* Added a validator for IncidentTypes (incidenttype-*.json).
* Fixed an issue where the -p flag in the *validate* command was not working.
* Added a validator for README.md files.
* Release notes validator will now run on: incident fields, indicator fields, incident types, dashboard and reputations.
* Fixed an issue where the validator of reputation(Indicator Type) did not check on the details field.
* Fixed an issue where the validator attempted validating non-existing files after deletions or name refactoring.
* Removed the *yml_type* argument in the *split-yml*, *extract-code* commands.
* Removed the *file_type* argument in the *generate-test-playbook* command.
* Fixed the *insecure* argument in *upload*.
* Added the *insecure* argument in *run-playbook*.
* Standardise the *-i --input*, *-o --output* to demisto-sdk commands.

### 0.4.3
* Fixed an issue where the incident and indicator field BC check failed.
* Support for linting and unit testing PowerShell integrations.

### 0.4.2
* Fixed an issue where validate failed on Windows.
* Added a validator to verify all branches are handled in conditional task in a playbook.
* Added a warning message when not running the latest sdk version.
* Added a validator to check that the root is connected to all tasks in the playbook.
* Added a validator for Dashboards (dashboard-*.json).
* Added a validator for Indicator Types (reputation-*.json).
* Added a BC validation for changing incident field type.
* Fixed an issue where init command would generate an invalid yml for scripts.
* Fixed an issue in misleading error message in v2 validation hook.
* Fixed an issue in v2 hook which now is set only on newly added scripts.
* Added more indicative message for errors in yaml files.
* Disabled pykwalify info log prints.

### 0.3.10
* Added a BC check for incident fields - changing from version is not allowed.
* Fixed an issue in create-content-artifacts where scripts in Packs in TestPlaybooks dir were copied with a wrong prefix.


### 0.3.9
* Added a validation that incident field can not be required.
* Added validation for fetch incident parameters.
* Added validation for feed integration parameters.
* Added to the *format* command the deletion of the *sourceplaybookid* field.
* Fixed an issue where *fieldMapping* in playbook did not pass the scheme validation.
* Fixed an issue where *create-content-artifacts* did not copy TestPlaybooks in Packs without prefix of *playbook-*.
* Added a validation the a playbook can not have a rolename set.
* Added to the image validator the new DBot default image.
* Added the fields: elasticcommonfields, quiet, quietmode to the Playbook schema.
* Fixed an issue where *validate* failed on integration commands without outputs.
* Added a new hook for naming of v2 integrations and scripts.


### 0.3.8
* Fixed an issue where *create-content-artifact* was not loading the data in the yml correctly.
* Fixed an issue where *unify* broke long lines in script section causing syntax errors


### 0.3.7
* Added *generate-docs* command to generate documentation file for integration, playbook or script.
* Fixed an issue where *unify* created a malformed integration yml.
* Fixed an issue where demisto-sdk **init** creates unit-test file with invalid import.


### 0.3.6
* Fixed an issue where demisto-sdk **validate** failed on modified scripts without error message.


### 0.3.5
* Fixed an issue with docker tag validation for integrations.
* Restructured repo source code.


### 0.3.4
* Saved failing unit tests as a file.
* Fixed an issue where "_test" file for scripts/integrations created using **init** would import the "HelloWorld" templates.
* Fixed an issue in demisto-sdk **validate** - was failing on backward compatiblity check
* Fixed an issue in demisto-sdk **secrets** - empty line in .secrets-ignore always made the secrets check to pass
* Added validation for docker image inside integrations and scripts.
* Added --use-git flag to **format** command to format all changed files.
* Fixed an issue where **validate** did not fail on dockerimage changes with bc check.
* Added new flag **--ignore-entropy** to demisto-sdk **secrets**, this will allow skip entropy secrets check.
* Added --outfile to **lint** to allow saving failed packages to a file.


### 0.3.3
* Added backwards compatibility break error message.
* Added schema for incident types.
* Added **additionalinfo** field to as an available field for integration configuration.
* Added pack parameter for **init**.
* Fixed an issue where error would appear if name parameter is not set in **init**.


### 0.3.2
* Fixed the handling of classifier files in **validate**.


### 0.3.1
* Fixed the handling of newly created reputation files in **validate**.
* Added an option to perform **validate** on a specific file.


### 0.3.0
* Added support for multi-package **lint** both with parallel and without.
* Added all parameter in **lint** to run on all packages and packs in content repository.
* Added **format** for:
    * Scripts
    * Playbooks
    * Integrations
* Improved user outputs for **secrets** command.
* Fixed an issue where **lint** would run pytest and pylint only on a single docker per integration.
* Added auto-complete functionality to demisto-sdk.
* Added git parameter in **lint** to run only on changed packages.
* Added the **run-playbook** command
* Added **run** command which runs a command in the Demisto playground.
* Added **upload** command which uploads an integration or a script to a Demisto instance.
* Fixed and issue where **validate** checked if release notes exist for new integrations and scripts.
* Added **generate-test-playbook** command which generates a basic test playbook for an integration or a script.
* **validate** now supports indicator fields.
* Fixed an issue with layouts scheme validation.
* Adding **init** command.
* Added **json-to-outputs** command which generates the yaml section for outputs from an API raw response.

### 0.2.6

* Fixed an issue with locating release notes for beta integrations in **validate**.

### 0.2.5

* Fixed an issue with locating release notes for beta integrations in **validate**.

### 0.2.4

* Adding image validation to Beta_Integration and Packs in **validate**.

### 0.2.3

* Adding Beta_Integration to the structure validation process.
* Fixing bug where **validate** did checks on TestPlaybooks.
* Added requirements parameter to **lint**.

### 0.2.2

* Fixing bug where **lint** did not return exit code 1 on failure.
* Fixing bug where **validate** did not print error message in case no release notes were give.

### 0.2.1

* **Validate** now checks that the id and name fields are identical in yml files.
* Fixed a bug where sdk did not return any exit code.

### 0.2.0

* Added Release Notes Validator.
* Fixed the Unifier selection of your python file to use as the code.
* **Validate** now supports Indicator fields.
* Fixed a bug where **validate** and **secrets** did not return exit code 1 on failure.
* **Validate** now runs on newly added scripts.

### 0.1.8

* Added support for `--version`.
* Fixed an issue in file_validator when calling `checked_type` method with script regex.

### 0.1.2
* Restructuring validation to support content packs.
* Added secrets validation.
* Added content bundle creation.
* Added lint and unit test run.

### 0.1.1

* Added new logic to the unifier.
* Added detailed README.
* Some small adjustments and fixes.

### 0.1.0

Capabilities:
* **Extract** components(code, image, description etc.) from a Demisto YAML file into a directory.
* **Unify** components(code, image, description etc.) to a single Demisto YAML file.
* **Validate** Demisto content files.
