# Changelog
* Fixed an issue where **format** did not update the test playbook from its pack.
* Fixed an issue where **validate** validated non integration images.
* Fixed an issue where **update-release-notes** did not identified old yml integrations and scripts.
* Added revision templates to the **update-release-notes** command.
* Fixed an issue where **update-release-notes** crashed when a file was renamed.
* Fixed an issue where **validate** failed on deleted files.
* Fixed an issue where **validate** validated all images instead of packs only.
* Fixed an issue where a warning was not printed in the **format** in case a non-supported file type is inputted.
* Fixed an issue where **validate** did not fail if no release notes were added when adding files to existing packs.
* Added handling of incorrect layout paths via the **format** command.
* Refactor **create-content-artifacts** command - Efficient artifacts creation and better logging.
* Fixed an issue where image and description files were not handled correctly by **validate** and **update-release-notes** commands.
* Fixed an issue where the **format** command didn't remove all extra fields in a file.
* Added an error in case an invalid id_set.json file is found while running the **validate** command.

# 1.1.11
* Added line number to secrets' path in **secrets** command report.
* Fixed an issue where **init** a community pack did not present the valid support URL.
* Fixed an issue where **init** offered a non relevant pack support type.
* Fixed an issue where **lint** did not pull docker images for powershell.
* Fixed an issue where **find-dependencies** did not find all the script dependencies.
* Fixed an issue where **find-dependencies** did not collect indicator fields as dependencies for playbooks.
* Updated the **validate** and the **secrets** commands to be less dependent on regex.
* Fixed an issue where **lint** did not run on circle when docker did not return ping.
* Updated the missing release notes error message (RN106) in the **Validate** command.
* Fixed an issue where **Validate** would return missing release notes when two packs with the same substring existed in the modified files.
* Fixed an issue where **update-release-notes** would add duplicate release notes when two packs with the same substring existed in the modified files.
* Fixed an issue where **update-release-notes** would fail to bump new versions if the feature branch was out of sync with the master branch.
* Fixed an issue where a non-descriptive error would be returned when giving the **update-release-notes** command a pack which can not be found.
* Added dependencies check for *widgets* in **find-dependencies** command.
* Added a `update-docker` flag to **format** command.
* Added a `json-to-outputs` flag to the **run** command.
* Added a verbose (`-v`) flag to **format** command.
* Fixed an issue where **download** added the prefix "playbook-" to the name of playbooks.

# 1.1.10
* Updated the **init** command. Relevant only when passing the *--contribution* argument.
   * Added the *--author* option.
   * The *support* field of the pack's metadata is set to *community*.
* Added a proper error message in the **Validate** command upon a missing description in the root of the yml.
* **Format** now works with a relative path.
* **Validate** now fails when all release notes have been excluded.
* Fixed issue where correct error message would not propagate for invalid images.
* Added the *--skip-pack-dependencies* flag to **validate** command to skip pack dependencies validation. Relevant when using the *-g* flag.
* Fixed an issue where **Validate** and **Format** commands failed integrations with `defaultvalue` field in fetch incidents related parameters.
* Fixed an issue in the **Validate** command in which unified YAML files were not ignored.
* Fixed an issue in **generate-docs** where scripts and playbooks inputs and outputs were not parsed correctly.
* Fixed an issue in the **openapi-codegen** command where missing reference fields in the swagger JSON caused errors.
* Fixed an issue in the **openapi-codegen** command where empty objects in the swagger JSON paths caused errors.
* **update-release-notes** command now accept path of the pack instead of pack name.
* Fixed an issue where **generate-docs** was inserting unnecessary escape characters.
* Fixed an issue in the **update-release-notes** command where changes to the pack_metadata were not detected.
* Fixed an issue where **validate** did not check for missing release notes in old format files.

# 1.1.9
* Fixed an issue where **update-release-notes** command failed on invalid file types.

# 1.1.8
* Fixed a regression where **upload** command failed on test playbooks.
* Added new *githubUser* field in pack metadata init command.
* Support beta integration in the commands **split-yml, extract-code, generate-test-playbook and generate-docs.**
* Fixed an issue where **find-dependencies** ignored *toversion* field in content items.
* Added support for *layoutscontainer*, *classifier_5_9_9*, *mapper*, *report*, and *widget* in the **Format** command.
* Fixed an issue where **Format** will set the `ID` field to be equal to the `name` field in modified playbooks.
* Fixed an issue where **Format** did not work for test playbooks.
* Improved **update-release-notes** command:
    * Write content description to release notes for new items.
    * Update format for file types without description: Connections, Incident Types, Indicator Types, Layouts, Incident Fields.
* Added a validation for feedTags param in feeds in **validate** command.
* Fixed readme validation issue in community support packs.
* Added the **openapi-codegen** command to generate integrations from OpenAPI specification files.
* Fixed an issue were release notes validations returned wrong results for *CommonScripts* pack.
* Added validation for image links in README files in **validate** command.
* Added a validation for default value of fetch param in feeds in **validate** command.
* Fixed an issue where the **Init** command failed on scripts.

# 1.1.7
* Fixed an issue where running the **format** command on feed integrations removed the `defaultvalue` fields.
* Playbook branch marked with *skipunavailable* is now set as an optional dependency in the **find-dependencies** command.
* The **feedReputation** parameter can now be hidden in a feed integration.
* Fixed an issue where running the **unify** command on JS package failed.
* Added the *--no-update* flag to the **find-dependencies** command.
* Added the following validations in **validate** command:
   * Validating that a pack does not depend on NonSupported / Deprecated packs.

# 1.1.6
* Added the *--description* option to the **init** command.
* Added the *--contribution* option to the **init** command which converts a contribution zip to proper pack format.
* Improved **validate** command performance time and outputs.
* Added the flag *--no-docker-checks* to **validate** command to skip docker checks.
* Added the flag *--print-ignored-files* to **validate** command to print ignored files report when the command is done.
* Added the following validations in **validate** command:
   * Validating that existing release notes are not modified.
   * Validating release notes are not added to new packs.
   * Validating that the "currentVersion" field was raised in the pack_metadata for modified packs.
   * Validating that the timestamp in the "created" field in the pack_metadata is in ISO format.
* Running `demisto-sdk validate` will run the **validate** command using git and only on committed files (same as using *-g --post-commit*).
* Fixed an issue where release notes were not checked correctly in **validate** command.
* Fixed an issue in the **create-id-set** command where optional playbook tasks were not taken into consideration.
* Added a prompt to the `demisto-sdk update-release-notes` command to prompt users to commit changes before running the release notes command.
* Added support to `layoutscontainer` in **validate** command.

#### 1.1.5
* Fixed an issue in **find-dependencies** command.
* **lint** command now verifies flake8 on CommonServerPython script.

#### 1.1.4
* Fixed an issue with the default output file name of the **unify** command when using "." as an output path.
* **Unify** command now adds contributor details to the display name and description.
* **Format** command now adds *isFetch* and *incidenttype* fields to integration yml.
* Removed the *feedIncremental* field from the integration schema.
* **Format** command now adds *feedBypassExclusionList*, *Fetch indicators*, *feedReputation*, *feedReliability*,
     *feedExpirationPolicy*, *feedExpirationInterval* and *feedFetchInterval* fields to integration yml.
* Fixed an issue in the playbooks schema.
* Fixed an issue where generated release notes were out of order.
* Improved pack dependencies detection.
* Fixed an issue where test playbooks were mishandled in **validate** command.

#### 1.1.3
* Added a validation for invalid id fields in indicators types files in **validate** command.
* Added default behavior for **update-release-notes** command.
* Fixed an error where README files were failing release notes validation.
* Updated format of generated release notes to be more user friendly.
* Improved error messages for the **update-release-notes** command.
* Added support for `Connections`, `Dashboards`, `Widgets`, and `Indicator Types` to **update-release-notes** command.
* **Validate** now supports scripts under the *TestPlaybooks* directory.
* Fixed an issue where **validate** did not support powershell files.

#### 1.1.2
* Added a validation for invalid playbookID fields in incidents types files in **validate** command.
* Added a code formatter for python files.
* Fixed an issue where new and old classifiers where mixed on validate command.
* Added *feedIncremental* field to the integration schema.
* Fixed error in the **upload** command where unified YMLs were not uploaded as expected if the given input was a pack.
* Fixed an issue where the **secrets** command failed due to a space character in the file name.
* Ignored RN validation for *NonSupported* pack.
* You can now ignore IF107, SC100, RP102 error codes in the **validate** command.
* Fixed an issue where the **download** command was crashing when received as input a JS integration or script.
* Fixed an issue where **validate** command checked docker image for JS integrations and scripts.
* **validate** command now checks scheme for reports and connections.
* Fixed an issue where **validate** command checked docker when running on all files.
* Fixed an issue where **validate** command did not fail when docker image was not on the latest numeric tag.
* Fixed an issue where beta integrations were not validated correctly in **validate** command.

#### 1.1.1
* fixed and issue where file types were not recognized correctly in **validate** command.
* Added better outputs for validate command.

#### 1.1.0
* Fixed an issue where changes to only non-validated files would fail validation.
* Fixed an issue in **validate** command where moved files were failing validation for new packs.
* Fixed an issue in **validate** command where added files were failing validation due to wrong file type detection.
* Added support for new classifiers and mappers in **validate** command.
* Removed support of old RN format validation.
* Updated **secrets** command output format.
* Added support for error ignore on deprecated files in **validate** command.
* Improved errors outputs in **validate** command.
* Added support for linting an entire pack.

#### 1.0.9
* Fixed a bug where misleading error was presented when pack name was not found.
* **Update-release-notes** now detects added files for packs with versions.
* Readme files are now ignored by **update-release-notes** and validation of release notes.
* Empty release notes no longer cause an uncaught error during validation.

#### 1.0.8
* Changed the output format of demisto-sdk secrets.
* Added a validation that checkbox items are not required in integrations.
* Added pack release notes generation and validation.
* Improved pack metadata validation.
* Fixed an issue in **validate** where renamed files caused an error

#### 1.0.4
* Fix the **format** command to update the `id` field to be equal to `details` field in indicator-type files, and to `name` field in incident-type & dashboard files.
* Fixed a bug in the **validate** command for layout files that had `sortValues` fields.
* Fixed a bug in the **format** command where `playbookName` field was not always present in the file.
* Fixed a bug in the **format** command where indicatorField wasn't part of the SDK schemas.
* Fixed a bug in **upload** command where created unified docker45 yml files were not deleted.
* Added support for IndicatorTypes directory in packs (for `reputation` files, instead of Misc).
* Fixed parsing playbook condition names as string instead of boolean in **validate** command
* Improved image validation in YAML files.
* Removed validation for else path in playbook condition tasks.

#### 1.0.3
* Fixed a bug in the **format** command where comments were being removed from YAML files.
* Added output fields: _file_path_ and _kind_ for layouts in the id-set.json created by **create-id-set** command.
* Fixed a bug in the **create-id-set** command Who returns Duplicate for Layouts with a different kind.
* Added formatting to **generate-docs** command results replacing all `<br>` tags with `<br/>`.
* Fixed a bug in the **download** command when custom content contained not supported content entity.
* Fixed a bug in **format** command in which boolean strings  (e.g. 'yes' or 'no') were converted to boolean values (e.g. 'True' or 'False').
* **format** command now removes *sourceplaybookid* field from playbook files.
* Fixed a bug in **generate-docs** command in which integration dependencies were not detected when generating documentation for a playbook.


#### 1.0.1
* Fixed a bug in the **unify** command when output path was provided empty.
* Improved error message for integration with no tests configured.
* Improved the error message returned from the **validate** command when an integration is missing or contains malformed fetch incidents related parameters.
* Fixed a bug in the **create** command where a unified YML with a docker image for 4.5 was copied incorrectly.
* Missing release notes message are now showing the release notes file path to update.
* Fixed an issue in the **validate** command in which unified YAML files were not ignored.
* File format suggestions are now shown in the relevant file format (JSON or YAML).
* Changed Docker image validation to fail only on non-valid ones.
* Removed backward compatibility validation when Docker image is updated.

#### 1.0.0
* Improved the *upload* command to support the upload of all the content entities within a pack.
* The *upload* command now supports the improved pack file structure.
* Added an interactive option to format integrations, scripts and playbooks with No TestPlaybooks configured.
* Added an interactive option to configure *conf.json* file with missing test playbooks for integrations, scripts and playbooks
* Added *download* command to download custom content from Demisto instance to the local content repository.
* Improved validation failure messages to include a command suggestion, wherever relevant, to fix the raised issue.
* Improved 'validate' help and documentation description
* validate - checks that scripts, playbooks, and integrations have the *tests* key.
* validate - checks that test playbooks are configured in `conf.json`.
* demisto-sdk lint - Copy dir better handling.
* demisto-sdk lint - Add error when package missing in docker image.
* Added *-a , --validate-all* option in *validate* to run all validation on all files.
* Added *-i , --input* option in *validate* to run validation on a specified pack/file.
* added *-i, --input* option in *secrets* to run on a specific file.
* Added an allowed hidden parameter: *longRunning* to the hidden integration parameters validation.
* Fixed an issue with **format** command when executing with an output path of a folder and not a file path.
* Bug fixes in generate-docs command given playbook as input.
* Fixed an issue with lint command in which flake8 was not running on unit test files.

#### 0.5.2
* Added *-c, --command* option in *generate-docs* to generate a specific command from an integration.
* Fixed an issue when getting README/CHANGELOG files from git and loading them.
* Removed release notes validation for new content.
* Fixed secrets validations for files with the same name in a different directory.
* demisto-sdk lint - parallelization working with specifying the number of workers.
* demisto-sdk lint - logging levels output, 3 levels.
* demisto-sdk lint - JSON report, structured error reports in JSON format.
* demisto-sdk lint - XML JUnit report for unit-tests.
* demisto-sdk lint - new packages used to accelerate execution time.
* demisto-sdk secrets - command now respects the generic whitelist, and not only the pack secrets.

#### 0.5.0
[PyPI History][1]

[1]: https://pypi.org/project/demisto-sdk/#history
### 0.4.9
* Fixed an issue in *generate-docs* where Playbooks and Scripts documentation failed.
* Added a graceful error message when executing the *run" command with a misspelled command.
* Added more informative errors upon failures of the *upload* command.
* format command:
    * Added format for json files: IncidentField, IncidentType, IndicatorField, IndicatorType, Layout, Dashboard.
    * Added the *-fv --from-version*, *-nv --no-validation* arguments.
    * Removed the *-t yml_type* argument, the file type will be inferred.
    * Removed the *-g use_git* argument, running format without arguments will run automatically on git diff.
* Fixed an issue in loading playbooks with '=' character.
* Fixed an issue in *validate* failed on deleted README files.

### 0.4.8
* Added the *max* field to the Playbook schema, allowing to define it in tasks loop.
* Fixed an issue in *validate* where Condition branches checks were case sensitive.

### 0.4.7
* Added the *slareminder* field to the Playbook schema.
* Added the *common_server*, *demisto_mock* arguments to the *init* command.
* Fixed an issue in *generate-docs* where the general section was not being generated correctly.
* Fixed an issue in *validate* where Incident type validation failed.

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
