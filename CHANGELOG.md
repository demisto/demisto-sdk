# Changelog
* When in private repo without `DEMSITO_SDK_GITHUB_TOKEN` configured, get_remote_file will take files from the local origin/master.
* Enhanced the **unify** command when giving input of a file and not a directory return a clear error message.
* Added a validation to ensure integrations are not skipped and at least one test playbook is not skipped for each integration or script.
* Added to the Content Tests support for `context_print_dt`, which queries the incident context and prints the result as a json.
* Added new validation for the `xsoar_config.json` file in the **validate** command.
* Added a version differences section to readme in **generate-docs** command.
* Added the *--docs-format* flag in the **integration-diff** command to get the output in README format.
* Added the *--input-old-version* and *--skip-breaking-changes* flags in the **generate-docs** command to get the
  details for the breaking section and to skip the breaking changes section.
* Added option to enter a dictionary or json of format `[{field_name:description}]` in the **json-to-outputs** command,
  with the `-d` flag.

# 1.4.0
* Enable passing a comma-separated list of paths for the `--input` option of the **lint** command.
* Added new validation of unimplemented test-module command in the code to the `XSOAR-linter` in the **lint** command.
* Fixed the **generate-docs** to handle integration authentication parameter.
* Added a validation to ensure that description and README do not contain the word 'Demisto'.
* Improved the deprecated message validation required from playbooks and scripts.
* Added the `--quite-bc-validation` flag for the **validate** command to run the backwards compatibility validation in quite mode (errors is treated like warnings).
* Fixed the **update release notes** command to display a name for old layouts.
* Added the ability to append to the pack README credit to contributors.
* Added identification for parameter differences in **integration-diff** command.
* Fixed **format** to use git as a default value.
* Updated the **upload** command to support reports.
* Fixed an issue where **generate-docs** command was displaying 'None' when credentials parameter display field configured was not configured.
* Fixed an issue where **download** did not return exit code 1 on failure.
* Updated the validation that incident fields' names do not contain the word incident will aplly to core packs only.
* Added a playbook validation to verify all conditional tasks have an 'else' path in **validate** command.
* Renamed the GitHub authentication token environment variable `GITHUB_TOKEN` to `DEMITO_SDK_GITHUB_TOKEN`.
* Added to the **update-release-notes** command automatic addition to git when new release notes file is created.
* Added validation to ensure that integrations, scripts, and playbooks do not contain the entity type in their names.
* Added the **convert** command to convert entities between XSOAR versions.
* Added the *--deprecate* flag in **format** command to deprecate integrations, scripts, and playbooks.
* Fixed an issue where ignoring errors did not work when running the **validate** command on specific files (-i).

# 1.3.9
* Added a validation verifying that the pack's README.md file is not equal to pack description.
* Fixed an issue where the **Assume yes** flag did not work properly for some entities in the **format** command.
* Improved the error messages for separators in folder and file names in the **validate** command.
* Removed the **DISABLE_SDK_VERSION_CHECK** environment variable. To disable new version checks, use the **DEMISTO_SDK_SKIP_VERSION_CHECK** envirnoment variable.
* Fixed an issue where the demisto-sdk version check failed due to a rate limit.
* Fixed an issue with playbooks scheme validation.

# 1.3.8
* Updated the **secrets** command to work on forked branches.

# 1.3.7
* Added a validation to ensure correct image and description file names.
* Fixed an issue where the **validate** command failed when 'display' field in credentials param in yml is empty but 'displaypassword' was provided.
* Added the **integration-diff** command to check differences between two versions of an integration and to return a report of missing and changed elements in the new version.
* Added a validation verifying that the pack's README.md file is not missing or empty for partner packs or packs contains use cases.
* Added a validation to ensure that the integration and script folder and file names will not contain separators (`_`, `-`, ` `).
* When formatting new pack, the **format** command will set the *fromversion* key to 5.5.0 in the new files without fromversion.

# 1.3.6
* Added a validation that core packs are not dependent on non-core packs.
* Added a validation that a pack name follows XSOAR standards.
* Fixed an issue where in some cases the `get_remote_file` function failed due to an invalid path.
* Fixed an issue where running **update-release-notes** with updated integration logo, did not detect any file changes.
* Fixed an issue where the **create-id-set** command did not identify unified integrations correctly.
* Fixed an issue where the `CommonTypes` pack was not identified as a dependency for all feed integrations.
* Added support for running SDK commands in private repositories.
* Fixed an issue where running the **init** command did not set the correct category field in an integration .yml file for a newly created pack.
* When formatting new contributed pack, the **format** command will set the *fromversion* key to 6.0.0 in the relevant files.
* If the environment variable "DISABLE_SDK_VERSION_CHECK" is define, the demisto-sdk will no longer check for newer version when running a command.
* Added the `--use-pack-metadata` flag for the **find-dependencies** command to update the calculated dependencies using the the packs metadata files.
* Fixed an issue where **validate** failed on scripts in case the `outputs` field was set to `None`.
* Fixed an issue where **validate** was failing on editing existing release notes.
* Added a validation for README files verifying that the file doesn't contain template text copied from HelloWorld or HelloWorldPremium README.

# 1.3.5
* Added a validation that layoutscontainer's id and name are matching. Updated the format of layoutcontainer to include update_id too.
* Added a validation that commands' names and arguments in core packs, or scripts' arguments do not contain the word incident.
* Fixed issue where running the **generate-docs** command with -c flag ran all the commands and not just the commands specified by the flag.
* Fixed the error message of the **validate** command to not always suggest adding the *description* field.
* Fixed an issue where running **format** on feed integration generated invalid parameter structure.
* Fixed an issue where the **generate-docs** command did not add all the used scripts in a playbook to the README file.
* Fixed an issue where contrib/partner details might be added twice to the same file, when using unify and create-content-artifacts commands
* Fixed issue where running **validate** command on image-related integration did not return the correct outputs to json file.
* When formatting playbooks, the **format** command will now remove empty fields from SetIncident, SetIndicator, CreateNewIncident, CreateNewIndicator script arguments.
* Added an option to fill in the developer email when running the **init** command.

# 1.3.4
* Updated the **validate** command to check that the 'additionalinfo' field only contains the expected value for feed required parameters and not equal to it.
* Added a validation that community/partner details are not in the detailed description file.
* Added a validation that the Use Case tag in pack_metadata file is only used when the pack contains at least one PB, Incident Type or Layout.
* Added a validation that makes sure outputs in integrations are matching the README file when only README has changed.
* Added the *hidden* field to the integration schema.
* Fixed an issue where running **format** on a playbook whose `name` does not equal its `id` would cause other playbooks who use that playbook as a sub-playbook to fail.
* Added support for local custom command configuration file `.demisto-sdk-conf`.
* Updated the **format** command to include an update to the description file of an integration, to remove community/partner details.

# 1.3.3
* Fixed an issue where **lint** failed where *.Dockerfile* exists prior running the lint command.
* Added FeedHelloWorld template option for *--template* flag in **demisto-sdk init** command.
* Fixed issue where **update-release-notes** deleted release note file if command was called more than once.
* Fixed issue where **update-release-notes** added docker image release notes every time the command was called.
* Fixed an issue where running **update-release-notes** on a pack with newly created integration, had also added a docker image entry in the release notes.
* Fixed an issue where `XSOAR-linter` did not find *NotImplementedError* in main.
* Added validation for README files verifying their length (over 30 chars).
* When using *-g* flag in the **validate** command it will now ignore untracked files by default.
* Added the *--include-untracked* flag to the **validate** command to include files which are untracked by git in the validation process.
* Improved the `pykwalify` error outputs in the **validate** command.
* Added the *--print-pykwalify* flag to the **validate** command to print the unchanged output from `pykwalify`.

# 1.3.2
* Updated the format of the outputs when using the *--json-file* flag to create a JSON file output for the **validate** and **lint** commands.
* Added the **doc-review** command to check spelling in .md and .yml files as well as a basic release notes review.
* Added a validation that a pack's display name does not already exist in content repository.
* Fixed an issue where the **validate** command failed to detect duplicate params in an integration.
* Fixed an issue where the **validate** command failed to detect duplicate arguments in a command in an integration.

# 1.3.1
* Fixed an issue where the **validate** command failed to validate the release notes of beta integrations.
* Updated the **upload** command to support indicator fields.
* The **validate** and **update-release-notes** commands will now check changed files against `demisto/master` if it is configured locally.
* Fixed an issue where **validate** would incorrectly identify files as renamed.
* Added a validation that integration properties (such as feed, mappers, mirroring, etc) are not removed.
* Fixed an issue where **validate** failed when comparing branch against commit hash.
* Added the *--no-pipenv* flag to the **split-yml** command.
* Added a validation that incident fields and incident types are not removed from mappers.
* Fixed an issue where the *c
reate-id-set* flag in the *validate* command did not work while not using git.
* Added the *hiddenusername* field to the integration schema.
* Added a validation that images that are not integration images, do not ask for a new version or RN

# 1.3.0
* Do not collect optional dependencies on indicator types reputation commands.
* Fixed an issue where downloading indicator layoutscontainer objects failed.
* Added a validation that makes sure outputs in integrations are matching the README file.
* Fixed an issue where the *create-id-set* flag in the **validate** command did not work.
* Added a warning in case no id_set file is found when running the **validate** command.
* Fixed an issue where changed files were not recognised correctly on forked branches in the **validate** and the **update-release-notes** commands.
* Fixed an issue when files were classified incorrectly when running *update-release-notes*.
* Added a validation that integration and script file paths are compatible with our convention.
* Fixed an issue where id_set.json file was re created whenever running the generate-docs command.
* added the *--json-file* flag to create a JSON file output for the **validate** and **lint** commands.

# 1.2.19
* Fixed an issue where merge id_set was not updated to work with the new entity of Packs.
* Added a validation that the playbook's version matches the version of its sub-playbooks, scripts, and integrations.

# 1.2.18
* Changed the *skip-id-set-creation* flag to *create-id-set* in the **validate** command. Its default value will be False.
* Added support for the 'cve' reputation command in default arg validation.
* Filter out generic and reputation command from scripts and playbooks dependencies calculation.
* Added support for the incident fields in outgoing mappers in the ID set.
* Added a validation that the taskid field and the id field under the task field are both from uuid format and contain the same value.
* Updated the **format** command to generate uuid value for the taskid field and for the id under the task field in case they hold an invalid values.
* Exclude changes from doc_files directory on validation.
* Added a validation that an integration command has at most one default argument.
* Fixing an issue where pack metadata version bump was not enforced when modifying an old format (unified) file.
* Added validation that integration parameter's display names are capitalized and spaced using whitespaces and not underscores.
* Fixed an issue where beta integrations where not running deprecation validations.
* Allowed adding additional information to the deprecated description.
* Fixing an issue when escaping less and greater signs in integration params did not work as expected.

# 1.2.17
* Added a validation that the classifier of an integration exists.
* Added a validation that the mapper of an integration exists.
* Added a validation that the incident types of a classifier exist.
* Added a validation that the incident types of a mapper exist.
* Added support for *text* argument when running **demisto-sdk update-release-notes** on the ApiModules pack.
* Added a validation for the minimal version of an indicator field of type grid.
* Added new validation for incident and indicator fields in classifiers mappers and layouts exist in the content.
* Added cache for get_remote_file to reducing failures from accessing the remote repo.
* Fixed an issue in the **format** command where `_dev` or `_copy` suffixes weren't removed from the `id` of the given playbooks.
* Playbook dependencies from incident and indicator fields are now marked as optional.
* Mappers dependencies from incident types and incident fields are now marked as optional.
* Classifier dependencies from incident types are now marked as optional.
* Updated **demisto-sdk init** command to no longer create `created` field in pack_metadata file
* Updated **generate-docs** command to take the parameters names in setup section from display field and to use additionalinfo field when exist.
* Using the *verbose* argument in the **find-dependencies** command will now log to the console.
* Improved the deprecated message validation required from integrations.
* Fixed an issue in the **generate-docs** command where **Context Example** section was created when it was empty.

# 1.2.16
* Added allowed ignore errors to the *IDSetValidator*.
* Fixed an issue where an irrelevant id_set validation ran in the **validate** command when using the *--id-set* flag.
* Fixed an issue were **generate-docs** command has failed if a command did not exist in commands permissions file.
* Improved a **validate** command message for missing release notes of api module dependencies.

# 1.2.15
* Added the *ID101* to the allowed ignored errors.

# 1.2.14
* SDK repository is now mypy check_untyped_defs complaint.
* The lint command will now ignore the unsubscriptable-object (E1136) pylint error in dockers based on python 3.9 - this will be removed once a new pylint version is released.
* Added an option for **format** to run on a whole pack.
* Added new validation of unimplemented commands from yml in the code to `XSOAR-linter`.
* Fixed an issue where Auto-Extract fields were only checked for newly added incident types in the **validate** command.
* Added a new warning validation of direct access to args/params dicts to `XSOAR-linter`.

# 1.2.13
* Added new validation of indicators usage in CommandResults to `XSOAR-linter`.
* Running **demisto-sdk lint** will automatically run on changed files (same behavior as the -g flag).
* Removed supported version message from the documentation when running **generate_docs**.
* Added a print to indicate backwards compatibility is being checked in **validate** command.
* Added a percent print when running the **validate** command with the *-a* flag.
* Fixed a regression in the **upload** command where it was ignoring `DEMISTO_VERIFY_SSL` env var.
* Fixed an issue where the **upload** command would fail to upload beta integrations.
* Fixed an issue where the **validate** command did not create the *id_set.json* file when running with *-a* flag.
* Added price change validation in the **validate** command.
* Added validations that checks in read-me for empty sections or leftovers from the auto generated read-me that should be changed.
* Added new code validation for *NotImplementedError* to raise a warning in `XSOAR-linter`.
* Added validation for support types in the pack metadata file.
* Added support for *--template* flag in **demisto-sdk init** command.
* Fixed an issue with running **validate** on master branch where the changed files weren't compared to previous commit when using the *-g* flag.
* Fixed an issue where the `XSOAR-linter` ran *NotImplementedError* validation on scripts.
* Added support for Auto-Extract feature validation in incident types in the **validate** command.
* Fixed an issue in the **lint** command where the *-i* flag was ignored.
* Improved **merge-id-sets** command to support merge between two ID sets that contain the same pack.
* Fixed an issue in the **lint** command where flake8 ran twice.

# 1.2.12
* Bandit now reports also on medium severity issues.
* Fixed an issue with support for Docker Desktop on Mac version 2.5.0+.
* Added support for vulture and mypy linting when running without docker.
* Added support for *prev-ver* flag in **update-release-notes** command.
* Improved retry support when building docker images for linting.
* Added the option to create an ID set on a specific pack in **create-id-set** command.
* Added the *--skip-id-set-creation* flag to **validate** command in order to add the capability to run validate command without creating id_set validation.
* Fixed an issue where **validate** command checked docker image tag on ApiModules pack.
* Fixed an issue where **find-dependencies** did not calculate dashboards and reports dependencies.
* Added supported version message to the documentation and release notes files when running **generate_docs** and **update-release-notes** commands respectively.
* Added new code validations for *NotImplementedError* exception raise to `XSOAR-linter`.
* Command create-content-artifacts additional support for **Author_image.png** object.
* Fixed an issue where schemas were not enforced for incident fields, indicator fields and old layouts in the validate command.
* Added support for **update-release-notes** command to update release notes according to master branch.

# 1.2.11
* Fixed an issue where the ***generate-docs*** command reset the enumeration of line numbering after an MD table.
* Updated the **upload** command to support mappers.
* Fixed an issue where exceptions were no printed in the **format** while the *--verbose* flag is set.
* Fixed an issue where *--assume-yes* flag did not work in the **format** command when running on a playbook without a `fromversion` field.
* Fixed an issue where the **format** command would fail in case `conf.json` file was not found instead of skipping the update.
* Fixed an issue where integration with v2 were recognised by the `name` field instead of the `display` field in the **validate** command.
* Added a playbook validation to check if a task script exists in the id set in the **validate** command.
* Added new integration category `File Integrity Management` in the **validate** command.

# 1.2.10
* Added validation for approved content pack use-cases and tags.
* Added new code validations for *CommonServerPython* import to `XSOAR-linter`.
* Added *default value* and *predefined values* to argument description in **generate-docs** command.
* Added a new validation that checks if *get-mapping-fields* command exists if the integration schema has *{ismappable: true}* in **validate** command.
* Fixed an issue where the *--staged* flag recognised added files as modified in the **validate** command.
* Fixed an issue where a backwards compatibility warning was raised for all added files in the **validate** command.
* Fixed an issue where **validate** command failed when no tests were given for a partner supported pack.
* Updated the **download** command to support mappers.
* Fixed an issue where the ***format*** command added a duplicate parameter.
* For partner supported content packs, added support for a list of emails.
* Removed validation of README files from the ***validate*** command.
* Fixed an issue where the ***validate*** command required release notes for ApiModules pack.

# 1.2.9
* Fixed an issue in the **openapi_codegen** command where it created duplicate functions name from the swagger file.
* Fixed an issue in the **update-release-notes** command where the *update type* argument was not verified.
* Fixed an issue in the **validate** command where no error was raised in case a non-existing docker image was presented.
* Fixed an issue in the **format** command where format failed when trying to update invalid Docker image.
* The **format** command will now preserve the **isArray** argument in integration's reputation commands and will show a warning if it set to **false**.
* Fixed an issue in the **lint** command where *finally* clause was not supported in main function.
* Fixed an issue in the **validate** command where changing any entity ID was not validated.
* Fixed an issue in the **validate** command where *--staged* flag did not bring only changed files.
* Fixed the **update-release-notes** command to ignore changes in the metadata file.
* Fixed the **validate** command to ignore metadata changes when checking if a version bump is needed.


# 1.2.8
* Added a new validation that checks in playbooks for the usage of `DeleteContext` in **validate** command.
* Fixed an issue in the **upload** command where it would try to upload content entities with unsupported versions.
* Added a new validation that checks in playbooks for the usage of specific instance in **validate** command.
* Added the **--staged** flag to **validate** command to run on staged files only.


# 1.2.7
* Changed input parameters in **find-dependencies** command.
   - Use ***-i, --input*** instead of ***-p, --path***.
   - Use ***-idp, --id-set-path*** instead of ***-i, --id-set-path***.
* Fixed an issue in the **unify** command where it crashed on an integration without an image file.
* Fixed an issue in the **format** command where unnecessary files were not skipped.
* Fixed an issue in the **update-release-notes** command where the *text* argument was not respected in all cases.
* Fixed an issue in the **validate** command where a warning about detailed description was given for unified or deprecated integrations.
* Improved the error returned by the **validate** command when running on files using the old format.

# 1.2.6
* No longer require setting `DEMISTO_README_VALIDATION` env var to enable README mdx validation. Validation will now run automatically if all necessary node modules are available.
* Fixed an issue in the **validate** command where the `--skip-pack-dependencies` would not skip id-set creation.
* Fixed an issue in the **validate** command where validation would fail if supplied an integration with an empty `commands` key.
* Fixed an issue in the **validate** command where validation would fail due to a required version bump for packs which are not versioned.
* Will use env var `DEMISTO_VERIFY_SSL` to determine if to use a secure connection for commands interacting with the Server when `--insecure` is not passed. If working with a local Server without a trusted certificate, you can set env var `DEMISTO_VERIFY_SSL=no` to avoid using `--insecure` on each command.
* Unifier now adds a link to the integration documentation to the integration detailed description.
* Fixed an issue in the **secrets** command where ignored secrets were not skipped.

# 1.2.5
* Added support for special fields: *defaultclassifier*, *defaultmapperin*, *defaultmapperout* in **download** command.
* Added -y option **format** command to assume "yes" as answer to all prompts and run non-interactively
* Speed up improvements for `validate` of README files.
* Updated the **format** command to adhere to the defined content schema and sub-schemas, aligning its behavior with the **validate** command.
* Added support for canvasContextConnections files in **format** command.

# 1.2.4
* Updated detailed description for community integrations.

# 1.2.3
* Fixed an issue where running **validate** failed on playbook with task that adds tags to the evidence data.
* Added the *displaypassword* field to the integration schema.
* Added new code validations to `XSOAR-linter`.
    * As warnings messages:
        * `demisto.params()` should be used only inside main function.
        * `demisto.args()` should be used only inside main function.
        * Functions args should have type annotations.
* Added `fromversion` field validation to test playbooks and scripts in **validate** command.

# 1.2.2
* Add support for warning msgs in the report and summary to **lint** command.
* Fixed an issue where **json-to-outputs** determined bool values as int.
* Fixed an issue where **update-release-notes** was crushing on `--all` flag.
* Fixed an issue where running **validate**, **update-release-notes** outside of content repo crushed without a meaningful error message.
* Added support for layoutscontainer in **init** contribution flow.
* Added a validation for tlp_color param in feeds in **validate** command.
* Added a validation for removal of integration parameters in **validate** command.
* Fixed an issue where **update-release-notes** was failing with a wrong error message when no pack or input was given.
* Improved formatting output of the **generate-docs** command.
* Add support for env variable *DEMISTO_SDK_ID_SET_REFRESH_INTERVAL*. Set this env variable to the refresh interval in minutes. The id set will be regenerated only if the refresh interval has passed since the last generation. Useful when generating Script documentation, to avoid re-generating the id_set every run.
* Added new code validations to `XSOAR-linter`.
    * As error messages:
        * Longer than 10 seconds sleep statements for non long running integrations.
        * exit() usage.
        * quit() usage.
    * As warnings messages:
        * `demisto.log` should not be used.
        * main function existence.
        * `demito.results` should not be used.
        * `return_output` should not be used.
        * try-except statement in main function.
        * `return_error` usage in main function.
        * only once `return_error` usage.
* Fixed an issue where **lint** command printed logs twice.
* Fixed an issue where *suffix* did not work as expected in the **create-content-artifacts** command.
* Added support for *prev-ver* flag in **lint** and **secrets** commands.
* Added support for *text* flag to **update-release-notes** command to add the same text to all release notes.
* Fixed an issue where **validate** did not recognize added files if they were modified locally.
* Added a validation that checks the `fromversion` field exists and is set to 5.0.0 or above when working or comparing to a non-feature branch in **validate** command.
* Added a validation that checks the certification field in the pack_metadata file is valid in **validate** command.
* The **update-release-notes** command will now automatically add docker image update to the release notes.

# 1.2.1
* Added an additional linter `XSOAR-linter` to the **lint** command which custom validates py files. currently checks for:
    * `Sys.exit` usages with non zero value.
    * Any `Print` usages.
* Fixed an issue where renamed files were failing on *validate*.
* Fixed an issue where single changed files did not required release notes update.
* Fixed an issue where doc_images required release-notes and validations.
* Added handling of dependent packs when running **update-release-notes** on changed *APIModules*.
    * Added new argument *--id-set-path* for id_set.json path.
    * When changes to *APIModule* is detected and an id_set.json is available - the command will update the dependent pack as well.
* Added handling of dependent packs when running **validate** on changed *APIModules*.
    * Added new argument *--id-set-path* for id_set.json path.
    * When changes to *APIModule* is detected and an id_set.json is available - the command will validate that the dependent pack has release notes as well.
* Fixed an issue where the find_type function didn't recognize file types correctly.
* Fixed an issue where **update-release-notes** command did not work properly on Windows.
* Added support for indicator fields in **update-release-notes** command.
* Fixed an issue where files in test dirs where being validated.


# 1.2.0
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
* Added fetch params checks to the **validate** command.

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

# 1.1.5
* Fixed an issue in **find-dependencies** command.
* **lint** command now verifies flake8 on CommonServerPython script.

# 1.1.4
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

# 1.1.3
* Added a validation for invalid id fields in indicators types files in **validate** command.
* Added default behavior for **update-release-notes** command.
* Fixed an error where README files were failing release notes validation.
* Updated format of generated release notes to be more user friendly.
* Improved error messages for the **update-release-notes** command.
* Added support for `Connections`, `Dashboards`, `Widgets`, and `Indicator Types` to **update-release-notes** command.
* **Validate** now supports scripts under the *TestPlaybooks* directory.
* Fixed an issue where **validate** did not support powershell files.

# 1.1.2
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

# 1.1.1
* fixed and issue where file types were not recognized correctly in **validate** command.
* Added better outputs for validate command.

# 1.1.0
* Fixed an issue where changes to only non-validated files would fail validation.
* Fixed an issue in **validate** command where moved files were failing validation for new packs.
* Fixed an issue in **validate** command where added files were failing validation due to wrong file type detection.
* Added support for new classifiers and mappers in **validate** command.
* Removed support of old RN format validation.
* Updated **secrets** command output format.
* Added support for error ignore on deprecated files in **validate** command.
* Improved errors outputs in **validate** command.
* Added support for linting an entire pack.

# 1.0.9
* Fixed a bug where misleading error was presented when pack name was not found.
* **Update-release-notes** now detects added files for packs with versions.
* Readme files are now ignored by **update-release-notes** and validation of release notes.
* Empty release notes no longer cause an uncaught error during validation.

# 1.0.8
* Changed the output format of demisto-sdk secrets.
* Added a validation that checkbox items are not required in integrations.
* Added pack release notes generation and validation.
* Improved pack metadata validation.
* Fixed an issue in **validate** where renamed files caused an error

# 1.0.4
* Fix the **format** command to update the `id` field to be equal to `details` field in indicator-type files, and to `name` field in incident-type & dashboard files.
* Fixed a bug in the **validate** command for layout files that had `sortValues` fields.
* Fixed a bug in the **format** command where `playbookName` field was not always present in the file.
* Fixed a bug in the **format** command where indicatorField wasn't part of the SDK schemas.
* Fixed a bug in **upload** command where created unified docker45 yml files were not deleted.
* Added support for IndicatorTypes directory in packs (for `reputation` files, instead of Misc).
* Fixed parsing playbook condition names as string instead of boolean in **validate** command
* Improved image validation in YAML files.
* Removed validation for else path in playbook condition tasks.

# 1.0.3
* Fixed a bug in the **format** command where comments were being removed from YAML files.
* Added output fields: _file_path_ and _kind_ for layouts in the id-set.json created by **create-id-set** command.
* Fixed a bug in the **create-id-set** command Who returns Duplicate for Layouts with a different kind.
* Added formatting to **generate-docs** command results replacing all `<br>` tags with `<br/>`.
* Fixed a bug in the **download** command when custom content contained not supported content entity.
* Fixed a bug in **format** command in which boolean strings  (e.g. 'yes' or 'no') were converted to boolean values (e.g. 'True' or 'False').
* **format** command now removes *sourceplaybookid* field from playbook files.
* Fixed a bug in **generate-docs** command in which integration dependencies were not detected when generating documentation for a playbook.


# 1.0.1
* Fixed a bug in the **unify** command when output path was provided empty.
* Improved error message for integration with no tests configured.
* Improved the error message returned from the **validate** command when an integration is missing or contains malformed fetch incidents related parameters.
* Fixed a bug in the **create** command where a unified YML with a docker image for 4.5 was copied incorrectly.
* Missing release notes message are now showing the release notes file path to update.
* Fixed an issue in the **validate** command in which unified YAML files were not ignored.
* File format suggestions are now shown in the relevant file format (JSON or YAML).
* Changed Docker image validation to fail only on non-valid ones.
* Removed backward compatibility validation when Docker image is updated.

# 1.0.0
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

# 0.5.2
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

# 0.5.0
[PyPI History][1]

[1]: https://pypi.org/project/demisto-sdk/#history
# 0.4.9
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

# 0.4.8
* Added the *max* field to the Playbook schema, allowing to define it in tasks loop.
* Fixed an issue in *validate* where Condition branches checks were case sensitive.

# 0.4.7
* Added the *slareminder* field to the Playbook schema.
* Added the *common_server*, *demisto_mock* arguments to the *init* command.
* Fixed an issue in *generate-docs* where the general section was not being generated correctly.
* Fixed an issue in *validate* where Incident type validation failed.

# 0.4.6
* Fixed an issue where the *validate* command did not identify CHANGELOG in packs.
* Added a new command, *id-set* to create the id set - the content dependency tree by file IDs.

# 0.4.5
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

# 0.4.4
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

# 0.4.3
* Fixed an issue where the incident and indicator field BC check failed.
* Support for linting and unit testing PowerShell integrations.

# 0.4.2
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

# 0.3.10
* Added a BC check for incident fields - changing from version is not allowed.
* Fixed an issue in create-content-artifacts where scripts in Packs in TestPlaybooks dir were copied with a wrong prefix.


# 0.3.9
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


# 0.3.8
* Fixed an issue where *create-content-artifact* was not loading the data in the yml correctly.
* Fixed an issue where *unify* broke long lines in script section causing syntax errors


# 0.3.7
* Added *generate-docs* command to generate documentation file for integration, playbook or script.
* Fixed an issue where *unify* created a malformed integration yml.
* Fixed an issue where demisto-sdk **init** creates unit-test file with invalid import.


# 0.3.6
* Fixed an issue where demisto-sdk **validate** failed on modified scripts without error message.


# 0.3.5
* Fixed an issue with docker tag validation for integrations.
* Restructured repo source code.


# 0.3.4
* Saved failing unit tests as a file.
* Fixed an issue where "_test" file for scripts/integrations created using **init** would import the "HelloWorld" templates.
* Fixed an issue in demisto-sdk **validate** - was failing on backward compatiblity check
* Fixed an issue in demisto-sdk **secrets** - empty line in .secrets-ignore always made the secrets check to pass
* Added validation for docker image inside integrations and scripts.
* Added --use-git flag to **format** command to format all changed files.
* Fixed an issue where **validate** did not fail on dockerimage changes with bc check.
* Added new flag **--ignore-entropy** to demisto-sdk **secrets**, this will allow skip entropy secrets check.
* Added --outfile to **lint** to allow saving failed packages to a file.


# 0.3.3
* Added backwards compatibility break error message.
* Added schema for incident types.
* Added **additionalinfo** field to as an available field for integration configuration.
* Added pack parameter for **init**.
* Fixed an issue where error would appear if name parameter is not set in **init**.


# 0.3.2
* Fixed the handling of classifier files in **validate**.


# 0.3.1
* Fixed the handling of newly created reputation files in **validate**.
* Added an option to perform **validate** on a specific file.


# 0.3.0
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

# 0.2.6

* Fixed an issue with locating release notes for beta integrations in **validate**.

# 0.2.5

* Fixed an issue with locating release notes for beta integrations in **validate**.

# 0.2.4

* Adding image validation to Beta_Integration and Packs in **validate**.

# 0.2.3

* Adding Beta_Integration to the structure validation process.
* Fixing bug where **validate** did checks on TestPlaybooks.
* Added requirements parameter to **lint**.

# 0.2.2

* Fixing bug where **lint** did not return exit code 1 on failure.
* Fixing bug where **validate** did not print error message in case no release notes were give.

# 0.2.1

* **Validate** now checks that the id and name fields are identical in yml files.
* Fixed a bug where sdk did not return any exit code.

# 0.2.0

* Added Release Notes Validator.
* Fixed the Unifier selection of your python file to use as the code.
* **Validate** now supports Indicator fields.
* Fixed a bug where **validate** and **secrets** did not return exit code 1 on failure.
* **Validate** now runs on newly added scripts.

# 0.1.8

* Added support for `--version`.
* Fixed an issue in file_validator when calling `checked_type` method with script regex.

# 0.1.2
* Restructuring validation to support content packs.
* Added secrets validation.
* Added content bundle creation.
* Added lint and unit test run.

# 0.1.1

* Added new logic to the unifier.
* Added detailed README.
* Some small adjustments and fixes.

# 0.1.0

Capabilities:
* **Extract** components(code, image, description etc.) from a Demisto YAML file into a directory.
* **Unify** components(code, image, description etc.) to a single Demisto YAML file.
* **Validate** Demisto content files.
