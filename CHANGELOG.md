# Changelog

[PyPI History][1]

[1]: https://pypi.org/project/demisto-sdk/#history

### 0.3.8
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
