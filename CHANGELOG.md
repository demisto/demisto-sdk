# Changelog
## 1.38.8 (2025-07-22)
### Fix
* Added ASM and Exposure Management to supported modules const. [#5012](https://github.com/demisto/demisto-sdk/pull/5012)


## 1.38.7 (2025-07-20)
### Feature
* Added support for `supportedModules` field in integrations, commands, and command arguments. [#4996](https://github.com/demisto/demisto-sdk/pull/4996)
* Added support for PLATFORM marketplace and multi-marketplace tags (e.g., <~XSIAM,PLATFORM>) in release notes. [#4982](https://github.com/demisto/demisto-sdk/pull/4982)

### Fix
* Fixed a syntax issue when printing feed parameters related errors. [#4995](https://github.com/demisto/demisto-sdk/pull/4995)
* Addressed `pkg_resources` deprecation warning by migrating to `importlib.metadata`. [#5002](https://github.com/demisto/demisto-sdk/pull/5002)
* Removed redundant `SupportedModulesValues` enum. [#5000](https://github.com/demisto/demisto-sdk/pull/5000)
* Updated `SupportedModulesValues` to support agentix. [#4996](https://github.com/demisto/demisto-sdk/pull/4996)

### Internal
* Fixed handling of playbooks in *GR110* validation. [#5008](https://github.com/demisto/demisto-sdk/pull/5008)
* Added the *IN164* validation. The validation ensures that a required param in an existing integration has a default value. [#5006](https://github.com/demisto/demisto-sdk/pull/5006)


## 1.38.6 (2025-07-07)
### Feature
* Add support for agentix content items- Action, Agent and enhancement of script. [#4920](https://github.com/demisto/demisto-sdk/pull/4920)
* Added new playbook validation *PB133* to ensure that test playbooks and test use cases referenced in the playbook YML exist. [#4976](https://github.com/demisto/demisto-sdk/pull/4976)
* Added new playbook validation *PB134* to ensure that the configuration docstring in playbook test use cases is valid. [#4976](https://github.com/demisto/demisto-sdk/pull/4976)

### Fix
* Fixed an issue where the ***xsoar-lint*** command would not run if the pack support level was set to 'developer'. [#4988](https://github.com/demisto/demisto-sdk/pull/4988)
* Fixed an issue where the ***doc-review*** command is not recognized if the *--release-notes* flag is specified. [#4987](https://github.com/demisto/demisto-sdk/pull/4987)
* Fixed an issue where the GR109 validation failed due to checking content items that are not supported by the platform. [#4990](https://github.com/demisto/demisto-sdk/pull/4990)

### Internal
* Removed default addition of `supportedModule` for content items where this field was not explicitly defined. [#4951](https://github.com/demisto/demisto-sdk/pull/4951)
* Bump `setuptools` version in pyproject.toml. [#4993](https://github.com/demisto/demisto-sdk/pull/4993)


## 1.38.5 (2025-06-29)
### Feature
* Added BA112 validation to enforce compliant policy naming for the "Preference Center" feature. [#4968](https://github.com/demisto/demisto-sdk/pull/4968)
* Created the following new validateion:
- ST112: Validate that any content item with a quick action command also has the supportsquickactions field in its top level yml.
- ST113: Validate that supportedModules can't be an empty list.
- BC115: Validate that no support modules are removed from an existing content item.
- GR109: Validate that if content item A depends on content item B, then content item B's supportedModules must include all supportedModules of content item A.
 [#4947](https://github.com/demisto/demisto-sdk/pull/4947)

### Fix
* Fixed an issue where prepare-content would create multiple playbooks for marketplaceV2. [#4981](https://github.com/demisto/demisto-sdk/pull/4981)

### Internal
* Changes in test data folder trigger the unit-tests hook in pre-commit. [#4972](https://github.com/demisto/demisto-sdk/pull/4972)


## 1.38.4 (2025-06-16)
### Feature
* Added the MyPy **demisto-sdk pre-commit** hook. [#4963](https://github.com/demisto/demisto-sdk/pull/4963)

### Fix
* Updated the **demisto-sdk split** command to catch the new format of the integration debug information, and updated the contribution converter script respectively. [#4958](https://github.com/demisto/demisto-sdk/pull/4958)

### Internal
* Updated the **demisto-sdk pre-commit** configuration to only run ruff on Python versions >= 3.7. [#4964](https://github.com/demisto/demisto-sdk/pull/4964)
* Added support for a new section in the conf.json file. [#4969](https://github.com/demisto/demisto-sdk/pull/4969)
* Removed mitmproxy package as it is no longer used. [#4952](https://github.com/demisto/demisto-sdk/pull/4952)
* Bumped werkzeug package from version 2.3.8 to 3.1.3. [#4858](https://github.com/demisto/demisto-sdk/pull/4858)


## 1.38.3 (2025-06-08)
### Feature
* Added support for the new `compliantpolicies` key in integrations and scripts. [#4953](https://github.com/demisto/demisto-sdk/pull/4953)


## 1.38.2 (2025-06-05)
### Feature
* Added the ability to un-skip a specific hook in a specific mode. [#4960](https://github.com/demisto/demisto-sdk/pull/4960)

### Fix
* Fixed XSIAM 3.x to hide classifiers and mappers parameters from configuration. [#4961](https://github.com/demisto/demisto-sdk/pull/4961)

### Internal
* Upgraded XSOAR 6 tenants in the content build to versions 6.13 and 6.14. [#4916](https://github.com/demisto/demisto-sdk/pull/4916)


## 1.38.1 (2025-05-25)
### Feature
* Removed the **mypy** hook from the ***pre-commit*** command since there is a new **mypy-in-docker** hook. [#4950](https://github.com/demisto/demisto-sdk/pull/4950)

### Fix
* Fixed an issue where creating a release note for an `ApiModule` also created release notes for deprecated integrations. [#4948](https://github.com/demisto/demisto-sdk/pull/4948)
* Fixed XSIAM tags utilization for platform pack's README files. [#4949](https://github.com/demisto/demisto-sdk/pull/4949)
* Added support for uploading Wizards exclusively to the XSOAR marketplace. [#4946](https://github.com/demisto/demisto-sdk/pull/4946)
* Fixed an issue where logging would fail when the *--show-diff-on-failure* flag was selected when running the ***pre-commit*** command.  [#4941](https://github.com/demisto/demisto-sdk/pull/4941)
* Fixed an issue where **fetch-assets** could appear as available for unsupported marketplaces in integration metadata. [#4943](https://github.com/demisto/demisto-sdk/pull/4943)

### Internal
* Fixed an issue related to the validation message of *IM109*. [#4936](https://github.com/demisto/demisto-sdk/pull/4936)


## 1.38.0 (2025-05-14)
### Feature
* Add the 'Result' section to SectionOrderValues and updated related validations. [#4930](https://github.com/demisto/demisto-sdk/pull/4930)
* Added the `isCloudProviderIntegration` field to the integration schema. [#4939](https://github.com/demisto/demisto-sdk/pull/4939)
* Update IN118 validation to exclude parameters of type 23 (engine_placeholder parameter). [#4929](https://github.com/demisto/demisto-sdk/pull/4929)
* Updated structure validation to include the 'triggers' section. [#4931](https://github.com/demisto/demisto-sdk/pull/4931)
* Added the `triggers` section to the integration schema. [#4934](https://github.com/demisto/demisto-sdk/pull/4934)

### Fix
* Fixed an issue where the **zip-packs** command created a pack metadata file with empty lists when the pack contained a split json list. [#4928](https://github.com/demisto/demisto-sdk/pull/4928)
* Fixed an issue where the **fetch-events** and **fetch-assets** functionalities were not available in the `platform` and `xpanse` marketplaces. [#4940](https://github.com/demisto/demisto-sdk/pull/4940)
* Fixed an issue where quick actions were available in non-platform marketplaces. [#4940](https://github.com/demisto/demisto-sdk/pull/4940)


## 1.37.5 (2025-05-11)
### Feature
* Added support for searching alerts by name in the `XsiamClient`. [#4914](https://github.com/demisto/demisto-sdk/pull/4914)
* Added support for polling alert state in the `XsiamClient`. [#4914](https://github.com/demisto/demisto-sdk/pull/4914)

### Fix
* Fixed an issue that caused Platform Packs `README.md` files to reference incorrect image URLs. [#4924](https://github.com/demisto/demisto-sdk/pull/4924)
* Fixed an issue where searching alerts by UUID in the `XsiamClient` would iterate over the first 100 results only. [#4914](https://github.com/demisto/demisto-sdk/pull/4914)
* Fixed an issue where polling playbook tasks by state would previously immediately timeout in the `XsoarClient`. [#4914](https://github.com/demisto/demisto-sdk/pull/4914)

### Internal
* Fixed logging for the **sdk-changelog** command. [#4932](https://github.com/demisto/demisto-sdk/pull/4932)
* Fixed an intermittent JSON serialization issue in **demisto-sdk validate** command that was causing validation failures in GitHub Actions. [#4921](https://github.com/demisto/demisto-sdk/pull/4921)
* Fixed an issue where the Github Action `process_pack`, in the contribution management repo, failed with exit code 0. [#4919](https://github.com/demisto/demisto-sdk/pull/4919)

## 1.37.4 (2025-05-04)
### Fix
* Fixed an issue in ***prepare-content*** command where the metadata.json file was being generated from the wrong file. [#4892](https://github.com/demisto/demisto-sdk/pull/4892)
* Fixed an issue in ***generate-unit-tests*** command where client init arguments where not used. [#4889](https://github.com/demisto/demisto-sdk/pull/4889)


## 1.37.3 (2025-04-21)
### Feature
* Added support for local custom command configuration file - `.demisto-sdk-conf` to ***download*** command. [#4912](https://github.com/demisto/demisto-sdk/pull/4912)

### Fix
* Fixed an issue in the ***upload*** command where it did not upload more than one pack at once. [#4904](https://github.com/demisto/demisto-sdk/pull/4904)

### Internal
* Added the `incident to alert` mechanism for the Platform marketplace. [#4913](https://github.com/demisto/demisto-sdk/pull/4913)


## 1.37.2 (2025-04-09)
### Fix
* Fixed an issue where ***pre-commit*** failed when run on new docker image. [#4905](https://github.com/demisto/demisto-sdk/pull/4905)
* Fixed an issue in the ***unify*** command where a hyphen in the pack id would cause parsing error. [#4900](https://github.com/demisto/demisto-sdk/pull/4900)


## 1.37.1 (2025-04-08)
### Feature
* Updated the integration template used in the ***init*** command to include the `sectionOrder` field. [#4890](https://github.com/demisto/demisto-sdk/pull/4890)

### Fix
* Fixed the processing of Platform content items to align with XSIAM content items processing. [#4898](https://github.com/demisto/demisto-sdk/pull/4898)


## 1.37.0 (2025-04-04)
### Breaking
* Removed ***lint*** command. [#4881](https://github.com/demisto/demisto-sdk/pull/4881)

### Feature
* Added allow-ignore-all-errors / iae flag. Use this flag to allow ignoring all errors in the build regardless of the set of ignorable errors in the config file. [#4878](https://github.com/demisto/demisto-sdk/pull/4878)
* Added the option to add content to the pack README of a new pack that was contributed through XSOAR UI. [#4684](https://github.com/demisto/demisto-sdk/pull/4684)

### Fix
* Updated log level for file dumps. [#4883](https://github.com/demisto/demisto-sdk/pull/4883)
* Added *dataSourceId* to Platform packs' metadata. [#4887](https://github.com/demisto/demisto-sdk/pull/4887)
* Fixed an issue where playbooks descriptions were not displayed correctly on the marketplace. [#4886](https://github.com/demisto/demisto-sdk/pull/4886)
* Fixed support for the newly introduced *supportedModules* field in Modeling Rules and Parsing Rules. [#4885](https://github.com/demisto/demisto-sdk/pull/4885)

### Internal
* Changed the unify process to add a constant of the pack version to each Python file. [#4844](https://github.com/demisto/demisto-sdk/pull/4844)
* Updated the ***test-content*** command to close successful incidents instead of deleting them during a test playbook run in XSOAR 6. [#4882](https://github.com/demisto/demisto-sdk/pull/4882)


## 1.36.4 (2025-03-21)
### Fix
* Fixed support for the newly introduced *supportedModules* field. [#4876](https://github.com/demisto/demisto-sdk/pull/4876) [#4874](https://github.com/demisto/demisto-sdk/pull/4874)
* Fixed an issue where certain validations would fail when executed from a local branch without a corresponding remote branch. [#4872](https://github.com/demisto/demisto-sdk/pull/4872)

### Internal
* Removed old validate from all builds. [#4862](https://github.com/demisto/demisto-sdk/pull/4862)


## 1.36.3 (2025-03-19)
### Fix
* Fixed support for the newly introduced *supportedModule* field. [#4871](https://github.com/demisto/demisto-sdk/pull/4871)


## 1.36.2 (2025-03-16)
### Feature
* Added support for playbook tags in metadata dump, and support for *supportedModules* field. [#4832](https://github.com/demisto/demisto-sdk/pull/4832)

### Fix
* Fixed an issue in external contributions pull requests flow where incorrect Git status fetching led to validation failures. [#4829](https://github.com/demisto/demisto-sdk/pull/4829)
* Fixed an issue where ***pre-commit*** failed on deleted content folders. [#4855](https://github.com/demisto/demisto-sdk/pull/4855)

### Internal
* Fixed an issue with GitHub actions. [#4856](https://github.com/demisto/demisto-sdk/pull/4856)
* Updated the Graph schemas to support *supportsquickactions* in the correct place. [#4853](https://github.com/demisto/demisto-sdk/pull/4853)


## 1.36.1 (2025-03-09)
### Fix
* Fixed an issue where content items recognized in the graph with the word "incident" and referenced in XSIAM content items using the word "alert" (e.g., `SearchAlertsV2` instead of `SearchIncidentsV2`) resulted in incorrect relationship creation. [#4787](https://github.com/demisto/demisto-sdk/pull/4787)
* Fixed an issue in the YML unifier which caused commands and scripts under packs whose names contained an apostrophe to return a syntax error during runtime in XSOAR. [#4840](https://github.com/demisto/demisto-sdk/pull/4840)
* Fixed an issue where the DOCKER_REGISTRY_URL wasn't getting the correct value from the .env file. [#4845](https://github.com/demisto/demisto-sdk/pull/4845)
* Fixed an issue in ***validate*** command related to XSIAM report file name containing png and json files. [#4848](https://github.com/demisto/demisto-sdk/pull/4848)
* Updated the env variable for docker user in the on-push.yml workflow. [#4851](https://github.com/demisto/demisto-sdk/pull/4851)

### Internal
* Updated the ***validate*** command summary message. [#4838](https://github.com/demisto/demisto-sdk/pull/4838)
* Improved **uploader** error parsing tool to always show a meaningful message. [#4846](https://github.com/demisto/demisto-sdk/pull/4846)


## 1.36.0 (2025-03-04)
### Feature
* Increased Docker container timeout when creating a new Docker image. [#4835](https://github.com/demisto/demisto-sdk/pull/4835)
* Added a new hook for validating the validate config file. The hook includes the following validations *VA100* - Validate that all errors appearing in the file actually exist. *VA101* - Validate that all errors appearing in the path_based mode appears in the use_git mode as well. *VA102* - Validate that there's no error code configured twice (once in the select and once in the use_git sections. *VA103* - Validate that all existing errors are configured. [#4819](https://github.com/demisto/demisto-sdk/pull/4819)

### Fix
* Fixed an issue where validate mistake <> in msgs for colors values. [#4834](https://github.com/demisto/demisto-sdk/pull/4834)
* Fixed an issue where Pack object would fail to obtain ignored errors without posting traceback. [#4819](https://github.com/demisto/demisto-sdk/pull/4819)

### Internal
* Fixed an issue where some unit-tests failed in github-actions CI. [#4833](https://github.com/demisto/demisto-sdk/pull/4833)
* Added support for hidden commands. [#4836](https://github.com/demisto/demisto-sdk/pull/4836)
* Added some functionalities to support testing playbooks use cases. [#4807](https://github.com/demisto/demisto-sdk/pull/4807)
* Update schemas for the platform marketplace. [#4839](https://github.com/demisto/demisto-sdk/pull/4839)
* Removed mocking mechanism in test-content command. [#4764](https://github.com/demisto/demisto-sdk/pull/4764)
* Renamed pytest report file. [#4634](https://github.com/demisto/demisto-sdk/pull/4634)
* Updated Graph objects to support the new quick action properties. [#4830](https://github.com/demisto/demisto-sdk/pull/4830)
* Added validate summary text file to the logs. [#4828](https://github.com/demisto/demisto-sdk/pull/4828)


## 1.35.1 (2025-02-24)
### Breaking
* Removed *DS106* (is valid description name) since it was duplicated by *DS104* (no description file) from the new validate. [#4774](https://github.com/demisto/demisto-sdk/pull/4774)

### Feature
* Locked the MyPy version to 1.14.1 in the *mypy-in-docker* ***pre-commit*** hook to ensure consistent type checking. [#4812](https://github.com/demisto/demisto-sdk/pull/4812)
* Added support for platform marketplace. [#4815](https://github.com/demisto/demisto-sdk/pull/4815)
* Improved implementation of *BC107* validation to allow adding *toversion* field to a content item as long as a new content item is added to replace it in the next version. [#4766](https://github.com/demisto/demisto-sdk/pull/4766)
* Added *LO100* validation. The validation verify of script names when used in the dynamic section of the layout. [#4792](https://github.com/demisto/demisto-sdk/pull/4792)
* Updated the message string of the new validate failures summary. [#4818](https://github.com/demisto/demisto-sdk/pull/4818)
* Added a "Mirroring" section to "SectionOrderValues" in order to support the new golden standard effort. [#4799](https://github.com/demisto/demisto-sdk/pull/4799)
* Improved implementation of the help message for the *--input* flag in the ***update-release-notes*** command. [#4784](https://github.com/demisto/demisto-sdk/pull/4784)
* Update the Graph parsers to support the new marketplace properties. [#4823](https://github.com/demisto/demisto-sdk/pull/4823)

### Fix
* Improved handling of mirroring when preparing content for marketplaces where the feature is unsupported by the platform. [#4795](https://github.com/demisto/demisto-sdk/pull/4795)
* Improved implementation of regex in ***prepare-content*** command to remove XSOAR unrelated version references, except in unique documentation cases. [#4798](https://github.com/demisto/demisto-sdk/pull/4798)
* Fixed an issue where info-logging in ***run*** command failed. [#4802](https://github.com/demisto/demisto-sdk/pull/4802)
* Fixed an issue where setting the marketplace entry to xsoar_on_prem in the configuration also caused the test to run on xsoar_saas. [#4803](https://github.com/demisto/demisto-sdk/pull/4803)
* Fixed a typo in the force merge message during content build regarding validations. [#4801](https://github.com/demisto/demisto-sdk/pull/4801)
* Fixed an issue where the *RN107* validation failed when releasing an update on case layouts. [#4814](https://github.com/demisto/demisto-sdk/pull/4814)
* Fixed an issue where *PB130* was running on unnecessary files. [#4793](https://github.com/demisto/demisto-sdk/pull/4793)
* Fixed an issue where *PB131* was not validating correctly in certain cases. [#4793](https://github.com/demisto/demisto-sdk/pull/4793)
* Fixed an issue where *PA114* falsely failed on new packs. [#4818](https://github.com/demisto/demisto-sdk/pull/4818)
* Fixed an issue where several validations git statuses were incorrect. [#4818](https://github.com/demisto/demisto-sdk/pull/4818)
* Fixed an issue where running ***format*** on a pre-processing rule would delete the script ID field, it is now retained. [#4805](https://github.com/demisto/demisto-sdk/pull/4805)
* Improved the visibility and formatting of error messages for the ***generate-docs***, ***split*** and the ***update-release-notes*** commands. [#4817](https://github.com/demisto/demisto-sdk/pull/4817)
* Fixed a typo in *RN116* error message. [#4809](https://github.com/demisto/demisto-sdk/pull/4809)
* Fixed an issue in *BA102* where Invalid content items would mistakenly fail for integration or script nested folders. [#4774](https://github.com/demisto/demisto-sdk/pull/4774)
* Fixed an issue where some validations would fail with the wrong file path in the error message. [#4774](https://github.com/demisto/demisto-sdk/pull/4774)
* Fixed an issue where pushing a Docker image to a Docker registry incorrectly returned a success message despite the operation failing. [#4825](https://github.com/demisto/demisto-sdk/pull/4825)
* Fixed an issue in ***pre-commit*** where debug level logs were not appearing in the log file. [#4822](https://github.com/demisto/demisto-sdk/pull/4822)

### Internal
* Fixed an issue where the ***update-release-notes*** command would add redundant message when updating docker image versions. [#4826](https://github.com/demisto/demisto-sdk/pull/4826)
* Added support for version_config in find_type_by_path. [#4816](https://github.com/demisto/demisto-sdk/pull/4816)


## 1.35.0 (2025-02-03)
### Fix
* Fixed an issue where the ***demisto-sdk setup-env*** command failed when no *file_paths* argument was provided. [#4791](https://github.com/demisto/demisto-sdk/pull/4791)
* Fixed an issue where the ***demisto-sdk validate*** command ran on the remote branch instead of the local current branch by default. [#4778](https://github.com/demisto/demisto-sdk/pull/4778)

### Internal
* Added support for setting the dependency minimum version in the pack metadata. [#4786](https://github.com/demisto/demisto-sdk/pull/4786)
* Added new *VC100* validation. Validates that version_config file schema is valid. [#4769](https://github.com/demisto/demisto-sdk/pull/4769)
* Added new *VC101* validation. Validates that versions in version_config file are continuous. [#4769](https://github.com/demisto/demisto-sdk/pull/4769)
* Added the **VERSION_CONFIG** file type. [#4794](https://github.com/demisto/demisto-sdk/pull/4794)
* Added the **test-use-case** command to test use-case flows on cloud machines. [#4658](https://github.com/demisto/demisto-sdk/pull/4658)


## 1.34.1 (2025-01-28)
### Feature
* Added support for `command_examples` paths to the `validate-content-paths` in the ***demisto-sdk pre-commit*** hook. [#4775](https://github.com/demisto/demisto-sdk/pull/4775)
* Added shorter flags *-i* for the *--input* option and *-o* for the *--output* option in the ***demisto-sdk split*** command to enhance usability. [#4785](https://github.com/demisto/demisto-sdk/pull/4785)

### Fix
* Fixed *ST111* validation error message. [#4779](https://github.com/demisto/demisto-sdk/pull/4779)
* Fixed an issue in *RN114* validation where the validation's error will no longer be raised when the latest playbook release notes format is used. [#4782](https://github.com/demisto/demisto-sdk/pull/4782)
* Fixed an issue where *RN111* validation would fail when a docker entry message was missing. [#4781](https://github.com/demisto/demisto-sdk/pull/4781)

### Internal
* Fixed an issue in the Docker proxy mechanism where ISO 8601 timestamps with nanosecond precision were not properly parsed. [#4783](https://github.com/demisto/demisto-sdk/pull/4783)
* The mocking mechanism in the ***demisto-sdk test-content*** command will be removed in upcoming versions of the demisto-sdk. [#4772](https://github.com/demisto/demisto-sdk/pull/4772)


## 1.34.0 (2025-01-21)
### Internal
* Reintroduce support for GAR DockerHub proxy when running in a Gitlab CI environment. [#4655](https://github.com/demisto/demisto-sdk/pull/4655)
* Updated *RM108* validation to allow absolute paths if the files are a part of content-assets. [#4683](https://github.com/demisto/demisto-sdk/pull/4683)


## 1.33.6 (2025-01-20)
### Feature
* Updated the ***update-release-notes*** command to handle changes in scripts and integration (using the objects under `content_graph`). [#4562](https://github.com/demisto/demisto-sdk/pull/4562)
* Updated the *RN103* validation to validate the new fill in templates: "%%UPDATE_CONTENT_ITEM_CHANGE_DESCRIPTION%%", "%%UPDATE_CONTENT_ITEM_DESCRIPTION%%", "%%UPDATE_CONTENT_ITEM_NAME%%", "%%UPDATE_CONTENT_ITEM_TYPE%%". [#4562](https://github.com/demisto/demisto-sdk/pull/4562)
* Added a summary to the ***validate*** command that informs the user for each validation error whether it’s forcemergeable, ignorable, or must be handled. [#4773](https://github.com/demisto/demisto-sdk/pull/4773)

### Fix
* Fixed an issue where some demisto-sdk command exception stack-traces were excessively long. [#4776](https://github.com/demisto/demisto-sdk/pull/4776)


## 1.33.5 (2025-01-14)
### Feature
* Modified the ***pre-commit*** command tests collections flow to collect all tests files in the same directory as a changed script for improved robustness. [#4761](https://github.com/demisto/demisto-sdk/pull/4761)
* Reduced commands startup time. [#4752](https://github.com/demisto/demisto-sdk/pull/4752)
* *RN111* will now fail when unnecessarily updating a docker image. [#4741](https://github.com/demisto/demisto-sdk/pull/4741)
* Added *IF109* to the new validation format. Checks whether an incident or indicator field has a valid required field value. [#4753](https://github.com/demisto/demisto-sdk/pull/4753)
* Added *IF117* to the new validation format. Checks whether an incident or indicator field aliases have a valid marketplaces field value. [#4753](https://github.com/demisto/demisto-sdk/pull/4753)

### Fix
* Fixed an issue in ***update-release-notes*** command will fail when handling special characters in the **--text** argument. [#4751](https://github.com/demisto/demisto-sdk/pull/4751)
* Fixed an issue where in some cases, parsing playbook related files would fail due to naming discrepancy. [#4758](https://github.com/demisto/demisto-sdk/pull/4758)
* Fixed an issue where the ***update-release-notes*** command would delete the version from the pack metadata when using the **-u** flag with an invalid value. [#4765](https://github.com/demisto/demisto-sdk/pull/4765)
* Locked poetry v1.8.5 version. [#4756](https://github.com/demisto/demisto-sdk/pull/4756)
* Fixed an issue where the *ST110* validation failed when adding the marketplaces key to the CaseLayout content item. [#4763](https://github.com/demisto/demisto-sdk/pull/4763)
* Updated ***pre-commit*** command **Ruff** Hook to use the *output-format* argument.  [#4767](https://github.com/demisto/demisto-sdk/pull/4767)

### Internal
* Added *IF118* to the new validation format. Checks if an alias of an incident field has it's own alias. [#4748](https://github.com/demisto/demisto-sdk/pull/4748)
* Added *PB121* to the new validation format. Checks if the inputs of a playbook that are intended to be fetched from the context are in the correct format. [#4702](https://github.com/demisto/demisto-sdk/pull/4702)


## 1.33.4 (2025-01-06)
### Breaking
* Started deprecation process for old validate. This flow will be deprecated and removed in the near future. Please use the new validate flow. [#4750](https://github.com/demisto/demisto-sdk/pull/4750)

### Feature
* Added support for validating CaseLayout content items in the *RN114* validation. [#4755](https://github.com/demisto/demisto-sdk/pull/4755)
* Updated the *ST110* validation to validate the "sectionOrder" and individual sections. Added new validation *ST111* which validates the existence of the same fields. [#4739](https://github.com/demisto/demisto-sdk/pull/4739)
* Updated the ***update-release-notes*** command to add Markdown formatting to the release notes of new playbooks that follow the new playbook description template.
 [#4735](https://github.com/demisto/demisto-sdk/pull/4735)

### Fix
* Fixed an issue where the `build-Devcontainer` Github action failed due to `file_path` being None in ***setup-environment*** command. [#4747](https://github.com/demisto/demisto-sdk/pull/4747)
* Fixed an issue where an incorrect marketplace reference was not properly removed from the code. [#4745](https://github.com/demisto/demisto-sdk/pull/4745)


## 1.33.3 (2025-01-01)
### Breaking
* The ***demisto-sdk convert*** command has been deprecated and is no longer available for use. [#4743](https://github.com/demisto/demisto-sdk/pull/4743)

### Feature
* Added *TR100* and *PB130* validations. Ensures that all silent Playbooks/Triggers have `is_silent = True`, and name/trigger_name, ID and file_name start with the `silent-` prefix. [#4740](https://github.com/demisto/demisto-sdk/pull/4740)
* Added *BA128* validation. Ensures script and integration command names don't start with a digit. [#4722](https://github.com/demisto/demisto-sdk/pull/4722)

### Internal
* Upgraded `pylint` library version to 3.3.2. [#4709](https://github.com/demisto/demisto-sdk/pull/4709)


## 1.33.2 (2024-12-29)
### Breaking
* Removed support for *DS107* and *RM106* validations. Ensures no "demisto" word in description and readme files for both new & old validate formats. [#4712](https://github.com/demisto/demisto-sdk/pull/4712)
* Changed the code of *RM116* - Validate that the readme file is not to short to *RM117* due to error code duplication. [#4712](https://github.com/demisto/demisto-sdk/pull/4712)

### Feature
* Excluded silent items from release notes validation. [#4720](https://github.com/demisto/demisto-sdk/pull/4720)
* Added *PB131* validation. Ensures every silent trigger points to a silent playbook, and vice versa. [#4670](https://github.com/demisto/demisto-sdk/pull/4670)
* Excluded silent-Playbooks/Triggers from the metadata. [#4692](https://github.com/demisto/demisto-sdk/pull/4692)
* Added support for Silent-Playbooks in the old-validate. [#4726](https://github.com/demisto/demisto-sdk/pull/4726)
* Added support for CaseLayouts and CaseFields content items paths to the `validate-content-paths` ***demisto-sdk pre-commit*** hook. [#4706](https://github.com/demisto/demisto-sdk/pull/4706)
* Added *PB132* validation. Ensures that silent playbooks do not have a README file. [#4723](https://github.com/demisto/demisto-sdk/pull/4723)
* Updated validation rules to allow the deletion of silent Playbooks and silent Triggers. [#4715](https://github.com/demisto/demisto-sdk/pull/4715)
* Added support for writing ***demisto-sdk pre-commit*** command results to files. [#4697](https://github.com/demisto/demisto-sdk/pull/4697)
* Moved the *CR101* validation to the new validation format. Checks if "Correlation Rule" files match standards to `validate_content_path`. [#4569](https://github.com/demisto/demisto-sdk/pull/4569)
* Added *PB130* validation. Checks whether the silent playbook name id and the *isSilent* key are set correctly. [#4662](https://github.com/demisto/demisto-sdk/pull/4662)

### Fix
* Fixed an issue where YmlSplitter attributes were being unintentionally updated. [#4713](https://github.com/demisto/demisto-sdk/pull/4713)
* Fixed an issue where *ST110* would incorrectly fail when adding the isSilent field. [#4716](https://github.com/demisto/demisto-sdk/pull/4716)
* Fixed an issue where the error message wasn't clear when attempting to upload a content item to an unsupported marketplace. [#4727](https://github.com/demisto/demisto-sdk/pull/4727)
* Changed the isSilent key to lower case. [#4728](https://github.com/demisto/demisto-sdk/pull/4728)
* Fixed an issue in the ***demisto-sdk modeling-rules*** command where colored logs were not printed properly. [#4733](https://github.com/demisto/demisto-sdk/pull/4733)
* Fixed an issue where *RM114* falsely failed when it concatenated "Packs/" twice to the file path. [#4717](https://github.com/demisto/demisto-sdk/pull/4717)
* Fixed an issue where *RN106* and *PA114* validations would fail on new packs. [#4710](https://github.com/demisto/demisto-sdk/pull/4710)
* Fixed an issue where YmlSplitter attributes were being unintentionally updated. [#4696](https://github.com/demisto/demisto-sdk/pull/4696)
* Fixed an issue where *RN111* would fail when it should not when the docker entry message was missing. [#4714](https://github.com/demisto/demisto-sdk/pull/4714)
* Fixed an issue where the "incident to alert" conversion was not applied to the metadata file during the execution of the **prepare-content** command. [#4736](https://github.com/demisto/demisto-sdk/pull/4736)
* Fixed an issue where *RN107* validation would fail on new content items and specific content types. [#4711](https://github.com/demisto/demisto-sdk/pull/4711)

### Internal
* Added the **generate-command-docs** script and a pre-commit hook to generate commands documentation. [#4664](https://github.com/demisto/demisto-sdk/pull/4664)


## 1.33.0 (2024-12-08)
### Feature
* Modified the ***demisto-sdk --release-notes*** command to print a markdown representation of the currently installed demisto-sdk changelog. [#4687](https://github.com/demisto/demisto-sdk/pull/4687)
* Added support for a new pack version_config.json file. [#4699](https://github.com/demisto/demisto-sdk/pull/4699)
* Updated the ***prepare-content*** command to replace all occurrences of an incorrect marketplace reference in the content. [#4659](https://github.com/demisto/demisto-sdk/pull/4659)
* The Demisto-SDK CLI has been upgraded to use Typer for command-line interface (CLI) management. [#4637](https://github.com/demisto/demisto-sdk/pull/4637)
* Added an isSilent key to the Playbook and Trigger schemas. [#4689](https://github.com/demisto/demisto-sdk/pull/4689)
* Updated the GR107 validation to fail once on each item, and the message will contain all deprecated items in use instead of failing multiple times. [#4667](https://github.com/demisto/demisto-sdk/pull/4667)

### Fix
* Fixed an issue where YmlSplitter attributes were being unintentionally updated. [#4695](https://github.com/demisto/demisto-sdk/pull/4695)
* Fixed an issue where *-t* flag was missing from ***update-release-notes*** command setup. [#4691](https://github.com/demisto/demisto-sdk/pull/4691)
* Fixed an issue where RN108 validation raised an exception when executed on a new pack. [#4700](https://github.com/demisto/demisto-sdk/pull/4700)
* Fixed an issue in the ***validate*** command where new files could not be parsed. [#4700](https://github.com/demisto/demisto-sdk/pull/4700)
* Fixed an issue in the ***validate*** command where .pack-ignore files could not be parsed. [#4700](https://github.com/demisto/demisto-sdk/pull/4700)
* Fixed an issue where using the *-i* flag with ***setup-env*** command would fail. [#4690](https://github.com/demisto/demisto-sdk/pull/4690)
* Fixed an issue where the ***generate-docs*** command failed to ignore hidden parameters. [#4589](https://github.com/demisto/demisto-sdk/pull/4589)
* Fixed an issue where logger was not initialized properly. [#4695](https://github.com/demisto/demisto-sdk/pull/4695)
* Fixed an issue where validate GR107 was failing on unrelated content-item when running on deprecated content-items. [#4667](https://github.com/demisto/demisto-sdk/pull/4667)

### Internal
* Fixed the demisto-sdk nightly's `run-end-to-end-tests-xsoar` step, and updated the `test-content` missing flags. [#4686](https://github.com/demisto/demisto-sdk/pull/4686)
* Added the deprecated ***merge-id-sets*** command to Typer app. [#4680](https://github.com/demisto/demisto-sdk/pull/4680)
* Update demisto-sdk commands documentation. [#4685](https://github.com/demisto/demisto-sdk/pull/4685)
* Fixed an issue where ***setup-env*** command would fail when `FILE_PATHS` argument was missing. [#4694](https://github.com/demisto/demisto-sdk/pull/4694)
* ***NOTICE:*** Demisto-SDK will soon stop supporting Python 3.9 [#4698](https://github.com/demisto/demisto-sdk/pull/4698)


## 1.32.5 (2024-11-24)
### Breaking
* Removed PA134 from the old validate. The validation ensures that the pack has exactly one category and that this category is valid. [#4673](https://github.com/demisto/demisto-sdk/pull/4673)

### Feature
* Modified PA103 validation (validate pack categories). The validation will now allow multiple categories for a single pack. [#4673](https://github.com/demisto/demisto-sdk/pull/4673)
* Modified the configuration section generated by the generate-docs command by removing navigation steps and generalizing the code to accommodate different Cortex platforms. [#4585](https://github.com/demisto/demisto-sdk/pull/4585)
* Added support for non-default registry ports when using custom docker images. i.e: 'registry:5000/repository/image:main' [#4674](https://github.com/demisto/demisto-sdk/pull/4674)
* Added support for utilizing content_status.json within content pipelines. [#4656](https://github.com/demisto/demisto-sdk/pull/4656)

### Fix
* Fixed an issue where ***demisto-sdk pre-commit*** inadvertently skipped all files when executed with the *--all-files* flag. [#4668](https://github.com/demisto/demisto-sdk/pull/4668)
* Fixed an issue where demisto-sdk commands would fail in some system setups. [#4666](https://github.com/demisto/demisto-sdk/pull/4666)
* Fixed an issue where logging would fail when linking PR to Jira issue in the GitHub workflow step. [#4649](https://github.com/demisto/demisto-sdk/pull/4649)
* Fixed an issue where logger crashed when imported as library. [#4657](https://github.com/demisto/demisto-sdk/pull/4657)
* Fixed an issue where logging would fail when creating a Docker image. [#4648](https://github.com/demisto/demisto-sdk/pull/4648)

### Internal
* Moved RN106 and RN107 to the new validate format. These validations ensure there are no missing release notes. [#4643](https://github.com/demisto/demisto-sdk/pull/4643)
* Fixed an issue where the git statuses of content objects related files were not calculated correctly. [#4643](https://github.com/demisto/demisto-sdk/pull/4643)


## 1.32.4 (2024-11-10)
### Breaking
* The following commands will be deprecated and removed entirely in the next SDK release in two weeks: convert, create-content-artifacts, create-id-set, extract-code and lint.
* Moved CJ102 to the new validate format. The validation's error number is now BA103 and it ensure that the tests section is either a non-empty list or "No tests".

### Fix
* Fixed an issue where getting a malformed file raised an non-indicative error.
* Fixed an issue where the **validate** and **create-id-set** commands would fail to process correctly when encountering null values in the filters or transformers fields.

### Internal
* Moved RN113 to the new validate format. The validation ensures that all the first level headers in the release note are valid content types.
* Moved RN115 to the new validate format. The validation ensure that the release notes first level headers are valid.

## 1.32.3
* Fixed an issue where integrations and scripts validations didn't run in builds. [#4609](https://github.com/demisto/demisto-sdk/pull/4609)
* Added BA127 new validation. The validation checks that the level of depth of the context output path in the yml is lower or equal to 5 in XSOAR supported content items. [#4490](https://github.com/demisto/demisto-sdk/pull/4490)
* Added RM116 validation to the new validate format. The validation ensure that every playbook has an image and that the image is located under doc_files folder. [#4538](https://github.com/demisto/demisto-sdk/pull/4538)
* Added Python 3.12 support. [#4598](https://github.com/demisto/demisto-sdk/pull/4598)
* Added the ***hidden:marketplacev2*** field to the StrictScript pydantic object since it was recently added to the script schema. [#4610](https://github.com/demisto/demisto-sdk/pull/4610)
* Removed IN161 - invalid siem marketplace from the old validate. [#4609](https://github.com/demisto/demisto-sdk/pull/4609)
* Fixed an issue where docker logged debug level messages as info level. [#4500](https://github.com/demisto/demisto-sdk/pull/4500)
* Improved docker registry logs. [#4601](https://github.com/demisto/demisto-sdk/pull/4601)
* Fixed the StrictScript pydantic object to contain the new field ***hidden:marketplacev2*** just as a field in Argument. [#4615](https://github.com/demisto/demisto-sdk/pull/4615)
* Fixed an issue where docker validation didn't run in new validate. [#4603](https://github.com/demisto/demisto-sdk/pull/4603)
* Fixed an issue where tasks calling playbooks were forced to have their names match the playbook ID. [#4602](https://github.com/demisto/demisto-sdk/pull/4602)
*  Modified the RM106 validation message to reflect the problem in the README file. [#4604](https://github.com/demisto/demisto-sdk/pull/4604)
* Update SDK documentation. [#4599](https://github.com/demisto/demisto-sdk/pull/4599)
* Moved RN111 validation to the new validate format. The validation ensures that the docker documented in the yml file matches the one in the Release Notes. [#4619](https://github.com/demisto/demisto-sdk/pull/4619)
* Reverted support for GAR DockerHub proxy when running in a Gitlab CI environment. [#4628](https://github.com/demisto/demisto-sdk/pull/4628)

## 1.32.2
* GR107 validation has been removed from the legacy validate command to enhance performance. [#4561](https://github.com/demisto/demisto-sdk/pull/4561)
* Added support in the schema for XSIAM custom hidden value. [#4584](https://github.com/demisto/demisto-sdk/pull/4584)
* Moved GR107 validation to the new validate format. The validation ensures that deprecated content items are not used in other content items. [#4561](https://github.com/demisto/demisto-sdk/pull/4561)
* Moved GR108 validation to the new validate format. The validation ensures that non-hidden packs do not depend on hidden packs. [#4590](https://github.com/demisto/demisto-sdk/pull/4590)
* Enhanced the Graph interface to support multi-threaded environments. [#4576](https://github.com/demisto/demisto-sdk/pull/4576)
* Moved GR101 validation to the new validate format. This validation checks whether the content item uses an item with a higher version (making it incompatible). [#4570](https://github.com/demisto/demisto-sdk/pull/4570)
* Removed the **validate** warnings when the higher version is lower is not supported by Cortex anymore. [#4570](https://github.com/demisto/demisto-sdk/pull/4570)
* Moved RM100 to the new validate format, The validation was split to 3 different validations RM100 - no empty sections, RM115 - no default sections, RM116 - readme not to short. [#4371](https://github.com/demisto/demisto-sdk/pull/4371)
* Moved GR102 validation to the new validate format. This validation checks whether a content item has to_version higher than another one it uses. [#4586](https://github.com/demisto/demisto-sdk/pull/4586)
* Removed the **validate** warnings when the source's to_version is higher than the general default version. [#4586](https://github.com/demisto/demisto-sdk/pull/4586)
* Moved PA124 validation to the new validate format. The validation ensures that core packs do not depend on non-core packs. [#4596](https://github.com/demisto/demisto-sdk/pull/4596)
* Fixed an issue where debug-logging in **upload** failed. [#4591](https://github.com/demisto/demisto-sdk/pull/4591)
* Fixed an issue where debug-logging in **test-modeling-rules** failed. [#4591](https://github.com/demisto/demisto-sdk/pull/4591)
* Fixed an issue where **lint** failed showing messages. [#4582](https://github.com/demisto/demisto-sdk/pull/4582)
* Fixed an issue where **generate-docs** command used un-ordered dependency lists, which resulted in redundant git changes. [#4533](https://github.com/demisto/demisto-sdk/pull/4533)
* Fixed an issue where debug-logging in **setup-env** failed. [#4597](https://github.com/demisto/demisto-sdk/pull/4597)
* Fixed an issue where the **update-release-notes** command was not properly detecting existing items in the release notes. [#4579](https://github.com/demisto/demisto-sdk/pull/4579)
* Upgrade the Neo4j version when working with the **content graph** in a local environment. [#4571](https://github.com/demisto/demisto-sdk/pull/4571)
* Added support for GAR DockerHub proxy when running in a Gitlab CI environment. [#4528](https://github.com/demisto/demisto-sdk/pull/4528)
* Added support for `pre-commit` hooks to save logs as Gitlab CI artifacts. [#4581](https://github.com/demisto/demisto-sdk/pull/4581)
* Moved RN116 validation to the new validation format. The validation ensures that the RN contains a first level header. [#4575](https://github.com/demisto/demisto-sdk/pull/4575)
* Upgrade pylint to 3.3.1 [#4594](https://github.com/demisto/demisto-sdk/pull/4594)
* Improved implementation of the GR103 validation. [#4568](https://github.com/demisto/demisto-sdk/pull/4568)

## 1.32.1
* Modified the `sdk-changelog` script, to include the release date for each version in the title. [#4553](https://github.com/demisto/demisto-sdk/pull/4553)
* Modified the **xsoar-lint** command to show GitHub Annotations for _errors_, when the `GITHUB_ACTIONS` environment key is set. _Warnings_ are shown when the `DEMISTO_SDK_XSOAR_LINTER_WARNING_ANNOTATIONS` and `GITHUB_ACTIONS` are set. [#4400](https://github.com/demisto/demisto-sdk/pull/4400)
* Fixed an issue where **create artifacts** failed logging in certain scenarios. [#4574](https://github.com/demisto/demisto-sdk/pull/4574)
* Moved RN112 to the new validate format. The validation ensure that if RN contains 'breaking change' then the breaking change release note exist and filled correctly. [#4559](https://github.com/demisto/demisto-sdk/pull/4559)
* Added the PA114 validation to the new **validate** command. The validation checks if the version in the `pack_metadata.json` file needs to be raised. [#4342](https://github.com/demisto/demisto-sdk/pull/4342)

## 1.32.0
* Moved IN136 to the new validate format as part of RM102. [#4535](https://github.com/demisto/demisto-sdk/pull/4535)
* Dropped support for Python 3.8. [#4531](https://github.com/demisto/demisto-sdk/pull/4531)
* Removed GR103 from the old format to enhance performance. [#4522](https://github.com/demisto/demisto-sdk/pull/4522)
* Moved feed's expirationPolicy validation to a new validation - IN163. [#4460](https://github.com/demisto/demisto-sdk/pull/4460)
* Modified the `--release-notes` flag which would previously support a specific changelog file format. Now it retrieves the release data from the GitHub tags info. [#4554](https://github.com/demisto/demisto-sdk/pull/4554)
* Moved RM102 and IN136 validation to the new format. Ensures context outputs in README and YML files match. [#4535](https://github.com/demisto/demisto-sdk/pull/4535)
* Moved RM110 validation to the new format. Ensuring all commands are documented in the README. [#4542](https://github.com/demisto/demisto-sdk/pull/4542)
* Enhanced the **format** command logs by trimming whitespaces. [#4529](https://github.com/demisto/demisto-sdk/pull/4529)
* Added 'StrictModelingRule' and 'StrictAssetsModelingRule' to the `ST110` validation. [#4560](https://github.com/demisto/demisto-sdk/pull/4560)
* Moved GR105 validation to the new format. Ensuring that each content item has a unique ID. [#4545](https://github.com/demisto/demisto-sdk/pull/4545)
* Added 'ReleaseNotesConfig' and 'PackMetadata' to the `ST110` validation. [#4541](https://github.com/demisto/demisto-sdk/pull/4541)
* Modified the `sdk-changelog` script which would previously generate all release notes in one section. Now it generates the changelog with different sections separated by headers Fixed, Breaking Changes, and Internal. [#4555](https://github.com/demisto/demisto-sdk/pull/4555)
* Modified the `mypy` pre-commit hook in the **pre-commit** command which would previously run locally. The hook now runs in Docker and is renamed to `mypy-in-docker`. [#4468](https://github.com/demisto/demisto-sdk/pull/4468)
* Added 'AssetsModelingRuleSchema' to the `ST110` validation. [#4519](https://github.com/demisto/demisto-sdk/pull/4519)
* Removed 'canvas' tab from LO107 validation as it is now supported by XSIAM. [#4544](https://github.com/demisto/demisto-sdk/pull/4544)
* Added support for a specific value in the hidden attribute of a script argument. [#4550](https://github.com/demisto/demisto-sdk/pull/4550)
* Moved GR103 validation to the new validate format. The validation ensures that content items use other content items only if they exist in the repository. Additionally, removed this validation from the old format to improve performance. [#4522](https://github.com/demisto/demisto-sdk/pull/4522)
* Fixed an issue in the init-validation script where it wasn't generating the correct execution mode for graph validations. [#4543](https://github.com/demisto/demisto-sdk/pull/4543)
* Fix an issue with **generate-docs** command when an integration is missing a description. [#4510](https://github.com/demisto/demisto-sdk/pull/4510)
* Fixed an issue where docker validations failed on API Modules in the new validate flow. [#4539](https://github.com/demisto/demisto-sdk/pull/4539)
* Fixed an issue where running `validate -a` on specific validations failed ignored content items. [#4539](https://github.com/demisto/demisto-sdk/pull/4539)
* Fixed an issue where RM106 failed on false positive cases of `demisto` word occurrence. [#4539](https://github.com/demisto/demisto-sdk/pull/4539)
* Fixed an issue where the GR106 validation would fail on test playbooks that are marked as reputation tests. [#4549](https://github.com/demisto/demisto-sdk/pull/4549)
* Fixed an issue where Threat Intel layouts created in the UI would fail when uploaded using the SDK upload command. [#4548](https://github.com/demisto/demisto-sdk/pull/4548)
* Fixed an issue where logs would not show up correctly. [#4514](https://github.com/demisto/demisto-sdk/pull/4514)
* Modified *nltk* version requirement to 3.9.1. [#4540](https://github.com/demisto/demisto-sdk/pull/4540)
* Removed support for the `Connection` content item type. [#4547](https://github.com/demisto/demisto-sdk/pull/4547)
* Deprecated. Removed the canvas-context-connections.yml schema's file. [#4546](https://github.com/demisto/demisto-sdk/pull/4546)
* Fixed an issue where the **run-test-playbook** command (used internally) reported incorrect results. [#4514](https://github.com/demisto/demisto-sdk/pull/4514)


## 1.31.11
* Fixed an issue in RM114 where **validate** would not catch problematic images when their file type was not `png` or when their declaration within the README had additional characters present in it. [#4512](https://github.com/demisto/demisto-sdk/pull/4512)
* Fixed an issue where the default validations would not run properly. [#4532](https://github.com/demisto/demisto-sdk/pull/4532)
* Modified the ST110 validation to allow null values in XISAM-Report's `default_template_id`. [#4525](https://github.com/demisto/demisto-sdk/pull/4525)
* Fixed an issue where the hidden files not uploaded to the artifact in github workflow. [#4534](https://github.com/demisto/demisto-sdk/pull/4534)

## 1.31.10
* The `--ignore` flag in the **validate** command no longer requires error codes to be listed under `ignorable_errors` in the config file. [#4509](https://github.com/demisto/demisto-sdk/pull/4509)
* Fixed an issue where the DS107 validation (descriptions shouldn't contain the phrase `demisto`) failed when the `Demisto Bot` was mentioned. [#4517](https://github.com/demisto/demisto-sdk/pull/4517)

## 1.31.9
* Modified ST110 validation. Improved validation logic and made structure_errors non-optional (return an empty list instead). [#4493](https://github.com/demisto/demisto-sdk/pull/4493)
* Fixed an issue where redundant Paramiko logs were still being displayed, following the change in SDK v1.31.8 by locking the Paramiko package dependency in v3.4.1.  [#4507](https://github.com/demisto/demisto-sdk/pull/4507)
* Moved RN115 validation to the new validate format. The validation ensures there're not more than one new release note file per pack. [#4501](https://github.com/demisto/demisto-sdk/pull/4501)
* Added authentication for pulling images in the ***pre-commit*** command when running in GitLab CI. [#4515](https://github.com/demisto/demisto-sdk/pull/4515)

## 1.31.8
* Added the `--ignore` flag to **validate**. [#4385](https://github.com/demisto/demisto-sdk/pull/4385)
* Added validation GR106, to ensure every modified test playbook is used by at least one content item. [#4446](https://github.com/demisto/demisto-sdk/pull/4446)
* Added a new **pre-commit** hook to prevent Python files from disabling `mypy` checks in the file level. [#4405](https://github.com/demisto/demisto-sdk/pull/4405)
* Added a new optional field, `marketplaces`, in the release notes config (e.g. `1_2_3.json`). Use it to choose marketplaces where breaking changes apply. When a list is not provided, the default is all marketplaces. Supports aggregated release notes and retroactive editing. [#4483](https://github.com/demisto/demisto-sdk/pull/4483)
* Added validation PB127 that verifies default keys exist where marketplace suffix keys exist in playbooks. (e.g. using `description:xsoar` now requires `description`). [#4401](https://github.com/demisto/demisto-sdk/pull/4401)
* Modified the ***unify*** and ***prepare-content*** commands to add a `demisto.debug` logging of the pack name and version, in Python files. [#4437](https://github.com/demisto/demisto-sdk/pull/4437)
* Fixed an issue where PA102 failed when on valid modeling rules. [#4497](https://github.com/demisto/demisto-sdk/pull/4497)
* Fixed an issue where reusing the **content graph** after a long period of inactivity resulted in a 409 error. [#4495](https://github.com/demisto/demisto-sdk/pull/4495)
* Added a *support* attribute to all content items in the **content graph**. [#4430](https://github.com/demisto/demisto-sdk/pull/4430)
* Locked the nltk version to 3.8.1, since 3.8.2 was surprisingly removed from PyPI. No effect on demisto-SDK users. [#4496](https://github.com/demisto/demisto-sdk/pull/4496)

## 1.31.7
* Added 'CaseLayoutRule' to the `ST110` validation. [#4491](https://github.com/demisto/demisto-sdk/pull/4491)
* Added 'GenericField', 'GenericModule', 'Job', 'List', 'Mapper', 'ModelingRule', 'ParsingRule' and 'PreProcessRule' to the `ST110` validation. [#4470](https://github.com/demisto/demisto-sdk/pull/4470)
* Added 'CaseLayout' to the `ST110` validation. [#4489](https://github.com/demisto/demisto-sdk/pull/4489)
* Added the `native_nightly_packs` attribute to the conf.json schema. [#4479](https://github.com/demisto/demisto-sdk/pull/4479)
* Added 'AssetsModelingRule' to the `ST110` validation. [#4486](https://github.com/demisto/demisto-sdk/pull/4486)
* Added 'XSIAMReport' to the `ST110` validation. [#4484](https://github.com/demisto/demisto-sdk/pull/4484)
* Modified the testing of modeling rules on XSIAM by splitting the process to multiple machines [#4441](https://github.com/demisto/demisto-sdk/pull/4441)
* Added 'IndicatorType' to the `ST110` validation. [#4485](https://github.com/demisto/demisto-sdk/pull/4485)
* Added 'CaseField' to the `ST110` validation. [#4488](https://github.com/demisto/demisto-sdk/pull/4488)
* Added 'Report', 'Trigger', 'Widget', 'Wizard', 'XDRCTemplate' and 'XSIAMDashboard' to the `ST110` validation. [#4478](https://github.com/demisto/demisto-sdk/pull/4478)
* Fixed an issue with the parallel logger not showing the thread id. [#4487](https://github.com/demisto/demisto-sdk/pull/4487)
* Moved PR100 and XD100 validations to run the `validate-content-path` **pre-commit** hook. These validations ensure the ParsingRule and XSIAM Dashboard filenames are valid. [#4476](https://github.com/demisto/demisto-sdk/pull/4476)
* Started supporting only a dict value for the "cloud_servers_api_keys" file provided. [#4480](https://github.com/demisto/demisto-sdk/pull/4480)
* Removed the deprecated `types-pkg-resources` package dependency. demisto-sdk will use the `types-setuptools` package instead. [#4474](https://github.com/demisto/demisto-sdk/pull/4474)
* Updated paramiko to v3.4.1, removing the warning that would occasionally show. [#4482](https://github.com/demisto/demisto-sdk/pull/#4482)

## 1.31.6
* Added **Classifier**, **Layout** and **LayoutRule** to the ST110 validation. [#4447](https://github.com/demisto/demisto-sdk/pull/4447)
* Added **Playbook** to the ST110 validation. [#4461](https://github.com/demisto/demisto-sdk/pull/4461)
* Added **CorrelationRule** to the ST110 validation. [#4462](https://github.com/demisto/demisto-sdk/pull/4462)
* Added **Dashboard** to the ST110 validation. [#4467](https://github.com/demisto/demisto-sdk/pull/4467)
* Added **GenericDefinition** to the ST110 validation. [#4469](https://github.com/demisto/demisto-sdk/pull/4469)
* ֹMoved RN114 validation to the new format. The validation verifies the release note's headers are valid. [#4327](https://github.com/demisto/demisto-sdk/pull/4327)
* Fixed an issue where **Integration** and **Script** save failed due to Enum parsing issues. [#4459](https://github.com/demisto/demisto-sdk/pull/4459)
* Fixed an issue where **XSIAM Report** objects would fail structure ***validate*** checks for having the *metadata* field, It's now added as optional. [#4472](https://github.com/demisto/demisto-sdk/pull/4472)
* Moved RN108 validation to the new validate format. The validation ensures a new pack doesn't have any release notes. [#4459](https://github.com/demisto/demisto-sdk/pull/4459)
* Applied the *toml-sort* hook on toml files in the repo. [#4453](https://github.com/demisto/demisto-sdk/pull/4453)
* Modified ***pre-commit*** and ***validate*** commands to use a specific files list during the contribution flow instead of relying on Git diff. [#4451](https://github.com/demisto/demisto-sdk/pull/4451)

## 1.31.5
* Added new validation ST110. Checks schema validness for *Integration*, *Script*, *Incident Field*, *Indicator Field* and *Generic Type* objects. [#4399](https://github.com/demisto/demisto-sdk/pull/4399)
* Added support for pack doc_files upload. [#4438](https://github.com/demisto/demisto-sdk/pull/4438)
* Fixed an issue in BA124 validation where the validation wasn't case sensitive. [#4450](https://github.com/demisto/demisto-sdk/pull/4450)
* Fixed an issue in the **download** command where a 'missing content' error was shown on playbook-type tasks of an uploaded playbook that was initially downloaded using this command. [#4445](https://github.com/demisto/demisto-sdk/pull/4445)
* Replaced project formatter from *Black* to *ruff-format* and removed the *Black* dev-dependency. [#4435](https://github.com/demisto/demisto-sdk/pull/4435)
* Modified the new validate **is_valid** method name to **obtain_invalid_content_items**. [#4448](https://github.com/demisto/demisto-sdk/pull/4448)
* Moved IN147 validation to the new validate format as code BC114. The validation ensures no fields were removed/modified from the integration yml for a predefined list of fields. [#4449](https://github.com/demisto/demisto-sdk/pull/4449)
* Moved PB124 validation to the new validate format. The validation ensures there're unhandled condition tasks in the playbook. [#4424](https://github.com/demisto/demisto-sdk/pull/4424)
* Added support for different api key file structure in **test-content** command. [#4442](https://github.com/demisto/demisto-sdk/pull/4442)
* Moved Tests/markteplace/Core_* and Approved_* files in content repo under the *Config* folder. [#4417](https://github.com/demisto/demisto-sdk/pull/4417)

## 1.31.4
* Removed DO106 - docker_not_on_the_latest_tag validation for the old validate. [#4429](https://github.com/demisto/demisto-sdk/pull/4429)
* Added documentation improvements to the **pre-commit** command. [#4421](https://github.com/demisto/demisto-sdk/pull/4421)
* Added support to replace incident to alert for deprecated content. [#4440](https://github.com/demisto/demisto-sdk/pull/4440)
* Fixed an issue in the **test-modeling-rule** command, where the table wasn't left aligned. [#4419](https://github.com/demisto/demisto-sdk/pull/4419)
* Added Improvements to ***validate-file-permission-changes*** **pre-commit** hook. [#4434](https://github.com/demisto/demisto-sdk/pull/4434)
* Fixed an issue where old validate failed without listing the invalid content items. [#4432](https://github.com/demisto/demisto-sdk/pull/4432)
* Added DS104 to the new validation format. The validation verifies that a Description file is present for an integration. [#4393](https://github.com/demisto/demisto-sdk/pull/4393)
* Added MR107 to the new validation format. Validate that the dataset name of a modeling rule shows in the xif and schema files match. [#4429](https://github.com/demisto/demisto-sdk/pull/4429)
* Moved MP107 and MP108 validations to the new validate format as BC113. The validation ensures no incident types and incident fields were removed from the mapper. [#4433](https://github.com/demisto/demisto-sdk/pull/4433)
* Added PR101 and MR108 to the new validate format. The validations check if the rule id and the rule name end with the correct suffixes. [#4415](https://github.com/demisto/demisto-sdk/pull/4415)
* Removed the following arguments from the (internal) **test-content** command: circleci, xsiam-machine, xsiam-servers-path, xsiam-servers-api-keys-path. [#4422](https://github.com/demisto/demisto-sdk/pull/4422)
* Added the *verbose=False* parameter to the *fetch* method call to minimize unnecessary output messages. [#4427](https://github.com/demisto/demisto-sdk/pull/4427)
* Removed the **validate-file-permissions-changes** pre-commit hook. [#4436](https://github.com/demisto/demisto-sdk/pull/4436)

## 1.31.3
* Removed IN150 due to invalid_siem_integration_name from both old and new validate flows. [#4420](https://github.com/demisto/demisto-sdk/pull/4420)
* Removed RM108 and RM112 from the old validate format. [#4408](https://github.com/demisto/demisto-sdk/pull/4408)
* Added the **-tpb** option to the **upload** command. When provided, all the test playbooks for the given pack will be uploaded. [#4402](https://github.com/demisto/demisto-sdk/pull/4402)
* Modified GR100, that checks whether a content item attempts to use other content items which are not supported in all of the marketplaces of the content item. [#4282](https://github.com/demisto/demisto-sdk/pull/4282)
* Added the ability to use git.Repo object to initialize GitUtil. [#4387](https://github.com/demisto/demisto-sdk/pull/4387)
* Added timestamp print in console. [#4412](https://github.com/demisto/demisto-sdk/pull/4412)
* Add a pre-commit hook to validate file permission/mode changes in Packs directory. [#4389](https://github.com/demisto/demisto-sdk/pull/4389)
* Fixed an issue where the relative path regex wasn't written correctly. This fix affect RM108 and RM114 in the new validate. [#4413](https://github.com/demisto/demisto-sdk/pull/4413)
* Fixed an issue where new validate failed when attempting to parse renamed files. [#4411](https://github.com/demisto/demisto-sdk/pull/4411)
* Fixed an issue where playbook saved due to a failed attempt to dump task object. [#4416](https://github.com/demisto/demisto-sdk/pull/4416)
* Added support for the (internal) ***test-content*** command to work properly with multiple cloud servers. [#4321](https://github.com/demisto/demisto-sdk/pull/4321)
* Moved CR102 to the new validate format. The validation checks 'search_window' existence and non-emptiness when 'execution_mode' == 'SCHEDULED'. [#4409](https://github.com/demisto/demisto-sdk/pull/4409)
* Fixed an issue where wrong untracked files were collected during running of ***pre-commit*** and ***validate*** in contribution PR use-case. [#4410](https://github.com/demisto/demisto-sdk/pull/4410)

## 1.31.2
* Added the *marketplaces* field to the widget schema. [#4396](https://github.com/demisto/demisto-sdk/pull/4396)
* Moved IF119 to the new validation format. Check whether a *selectValue* key in an *incidentField* of type *singleSelect* do not contain multiple or only empty options. [#4277](https://github.com/demisto/demisto-sdk/pull/4277)
* Fixed an issue where IN121 in the new validate flow and IN148 in the old validate flow failed when running on content items with XSOAR on prem and XSOAR SAAS Marketplaces. [#4398](https://github.com/demisto/demisto-sdk/pull/4398)
* Fixed an issue where ***upload*** command failed locally due to missing lock file. [#4397](https://github.com/demisto/demisto-sdk/pull/4397)
* Fixed an issue where ***pre-commit*** and ***validate*** commands collected invalid untracked files when running on contribution PR. [#4394](https://github.com/demisto/demisto-sdk/pull/4394)

## 1.31.1
* Added an option to specify a marketplace for certain playbook fields: All input fields: *key*, *value*, *description*, *required*, *playbookInputKey*. The following task fields: *scriptId*, *scriptarguments*, *loop.scriptArguments*, *message*, *form*. The task id mappings (for example the first task can be converted by "0" -> "0:xsoar"). The *left* and *right* options of *condition*/*builtincondition* task fields (and their nested fields). [#4375](https://github.com/demisto/demisto-sdk/pull/4375)
* Added the *-h* option as a short option for the *--help* flag in ***typer***-based commands. [#4350](https://github.com/demisto/demisto-sdk/pull/4350)
* Modified the **error-code** command to show information using the new BaseValidator standard. When such isn't available, defaults to legacy-style inforamtion. [#4374](https://github.com/demisto/demisto-sdk/pull/4374)
* Added support to **run-specific-validations** flag to the new validate format. [#4380](https://github.com/demisto/demisto-sdk/pull/4380)
* Modified PA107 to fail when the key **marketplaces** is missing from the pack_metadata.json file. [#4379](https://github.com/demisto/demisto-sdk/pull/4379)
* Added a *--fix* option to DA100 and fixed the incorrect check in DA101. [#4381](https://github.com/demisto/demisto-sdk/pull/4381)
* Fixed an issue where **pre-commit** and **validate** commands ignored changed files when running on an external contribution PR. [#4351](https://github.com/demisto/demisto-sdk/pull/4351)
* Fixed an issue where RN103 failed on newly added packs due to missing release notes. [#4383](https://github.com/demisto/demisto-sdk/pull/4383)
* Fixed an issue where the *auto_update_docker_image* field was not updated correctly in the the content-graph. [#4287](https://github.com/demisto/demisto-sdk/pull/4287)
* Moved PB125 to the new validation format. The validation checks that a playbook condition task doesn't has only a default nexttask. [#4365](https://github.com/demisto/demisto-sdk/pull/4365)
* Moved PB114, PB119 to the new validation format. [#4348](https://github.com/demisto/demisto-sdk/pull/4348)
* Added support for different validation modes (-i, -a, -g) was added to the new validate command. [#4301](https://github.com/demisto/demisto-sdk/pull/4301)
* Moved PB115 to the new validation format. The validation checks if the 'quietmode' field of all tasks in playbook are not in default value. [#4366](https://github.com/demisto/demisto-sdk/pull/4366)
* Moved PB116 to the new format. The validation checks that indicator playbooks stop on error. [#4364](https://github.com/demisto/demisto-sdk/pull/4364)
* Moved PB109 to the new validate format. The validation checks that taskid field and id field under task field contains equal values. [#4358](https://github.com/demisto/demisto-sdk/pull/4358)
* Moved DS108 to the new validation format. The validation ensures that there's a dot at the end of each description line. [#4339](https://github.com/demisto/demisto-sdk/pull/4339)
* Moved PB122 to the new validation format. Validate whether branches of built-in conditional tasks are handled properly. [#4363](https://github.com/demisto/demisto-sdk/pull/4363)
* Modified MR103 to a path validation. Validates that the file names are the same as its folder. [#4376](https://github.com/demisto/demisto-sdk/pull/4376)
* Moved MR101 to the new validation format and combined it with MR102. Validates that the modeling rule yml file contains the schema and rules keys and that they are empty. [#4368](https://github.com/demisto/demisto-sdk/pull/4368)
* Moved RM107 to the new validation format. The validation checks that all placeholders are removed and all sections are filled in the readme files. [#4373](https://github.com/demisto/demisto-sdk/pull/4373)
* Modified IMAGES_BATCH variable to be configurable per environment. [#4382](https://github.com/demisto/demisto-sdk/pull/4382)
* Moved PB106 to new validation format. The validation checks if the playbook uses a specific instance. [#4360](https://github.com/demisto/demisto-sdk/pull/4360)
* Moved the RP102 to the new validation format. The validation checks wether the id field equals the details field in an indicator type [#4355](https://github.com/demisto/demisto-sdk/pull/4355)
* Moved MR106 to the new validation format. The validation verifies the types in schema files of modeling rules. [#4372](https://github.com/demisto/demisto-sdk/pull/4372)
* Moved RP103 to the new validation format. The validation make sure the indicator type id is valid. (can include letters, numbers whitespaces, ampersands and underscores.) [#4361](https://github.com/demisto/demisto-sdk/pull/4361)

## 1.31.0
* Fixed an issue where the logic for retrieving the latest Docker image was based on the entire tag (x.y.z.abcde) instead of just the last part of the image tag (_._._.abcde). Only the last part will now be used, per demisto/dockerfiles convention. [#4294](https://github.com/demisto/demisto-sdk/pull/4294)
* demist-sdk **lint** command is deprecated and should be fully removed from the SDK on September 1st. Please use the **pre-commit** command instead. [#4336](https://github.com/demisto/demisto-sdk/pull/4336)
* Removed support for IN124 - 'is param valid is hidden' validation from old-validate flow and prevent the validation from being ignored. The validation and the related information can be found in the new-validate flow. [#4317](https://github.com/demisto/demisto-sdk/pull/4317)
* Added support for new XSIAM content items - Case Fields, Case layouts and Case Layout Rules. [#4240](https://github.com/demisto/demisto-sdk/pull/4240)
* Added DS101 to the new validation format. Check if the beta disclaimer exists in the detailed description. [#4289](https://github.com/demisto/demisto-sdk/pull/4289)
* Added the `--force` flag to the **generate-docs** command to force the README.md generation instead of use version control to update the doc. [#4303](https://github.com/demisto/demisto-sdk/pull/4303)
* Added DS105 to the new validation format. "check if DESCRIPTION file contains contribution details" [#4347](https://github.com/demisto/demisto-sdk/pull/4347)
* Added DS106 to the new validation format. "Check if the description file exist and the name is valid" [#4357](https://github.com/demisto/demisto-sdk/pull/4357)
* updated the tenacity version to fix an installation error [#4352](https://github.com/demisto/demisto-sdk/pull/4352)
* Fixed an issue where the **pre-commit** command would fail on simple repository due to a missing `docker_native_image_config.json` file. [#4314](https://github.com/demisto/demisto-sdk/pull/4314)
* Fixed an issue in the **download** command where downloading with `force` and `run-format` flags did not merge YML fields. [#4328](https://github.com/demisto/demisto-sdk/pull/4328)
* Fixed an issue in **generate-docs** where integration commands arguments had missing descriptions. [#4320](https://github.com/demisto/demisto-sdk/pull/4320)
* Fixed an issue where validations searching for `demisto` in strings would find it in URLs (`/demisto/content`). [#4341](https://github.com/demisto/demisto-sdk/pull/4341)
* Fixed an issue where **generate-docs** command couldn't find the sections within the integration README.md when updating documentation for modified commands. [#4303](https://github.com/demisto/demisto-sdk/pull/4303)
* Fixed an issue where modified command names were treated as a new command. [#4303](https://github.com/demisto/demisto-sdk/pull/4303)
* Fixed the **update-release-notes** command to support the right template for incident fields, incident types, layouts, generic objects, indicator types, and indicator fields. [#4304](https://github.com/demisto/demisto-sdk/pull/4304)
* Fixed an issue in the **pre-commit** command where if the `DEMISTO_DEFAULT_BRANCH` environment variable was set to something other than "master", the command would fail. [#4325](https://github.com/demisto/demisto-sdk/pull/4325)
* Fixed an issue where **validate-content-path** checked suffixes of test- or doc-files [#4337](https://github.com/demisto/demisto-sdk/pull/4337)
* Fixed an issue where **format** did not work with private github repositories. [#4313](https://github.com/demisto/demisto-sdk/pull/4313)
* Fixed an issue in the **format** command where using the `--deprecate` flag would not properly work on beta integrations. [#4332](https://github.com/demisto/demisto-sdk/pull/4332)
* Modified the RM108 validation to follow the new validation format. [#4275](https://github.com/demisto/demisto-sdk/pull/4275)
* Modeled base_playbook tasks into objects to ease on the use in various flows. [#4343](https://github.com/demisto/demisto-sdk/pull/4343)
* Added a new flow that uploads a playbook execution report JSON to the artifacts bucket. [#4284](https://github.com/demisto/demisto-sdk/pull/4284)
* Started adaption for relative paths enforcement in the upload flow - The flow will now attempt to create a json file including a dict objects of all the image paths appears in the markdown files in relative path formats. [#4338](https://github.com/demisto/demisto-sdk/pull/4338)
* Updated the `artifacts_bucket` argument of the test-content command to be optional. [#4334](https://github.com/demisto/demisto-sdk/pull/4334)
* Modified the test-pre-commit-command validate hook to run only BA100 validation. [#4336](https://github.com/demisto/demisto-sdk/pull/4336)
* Converted the PB105 validation to the new format. The validation verifies the playbook doesn't contain deleteContext with all=Yes. [#4356](https://github.com/demisto/demisto-sdk/pull/4356)
* Moved PB108 to the new validate format. The validate checks that the 'taskid' and the 'id' under the 'task' field are from UUID format. [#4359](https://github.com/demisto/demisto-sdk/pull/4359)
* Modified the MR100 validation to follow the new validation format. [#4331](https://github.com/demisto/demisto-sdk/pull/4331)
* Added PB126 to the new validation format. Ensure that conditional tasks have more than path which is not the default one [#4349](https://github.com/demisto/demisto-sdk/pull/4349)
* Added the `removed_integration_parameter` validation to the new validate as `NoRemovedIntegrationParametersValidator`. [#4354](https://github.com/demisto/demisto-sdk/pull/4354)
* Modified validations RN103 and RN104 to follow the new validations format. [#4275](https://github.com/demisto/demisto-sdk/pull/4275)
* Added the PB103 to the new validation format. Validate whether there is an unconnected task. [#4340](https://github.com/demisto/demisto-sdk/pull/4340)

## 1.30.0
* Started a deprecation process of the **lint** command. It will be fully removed soon. Use **demisto-sdk pre-commit** instead. [#4286](https://github.com/demisto/demisto-sdk/pull/4286)
* Added support for Python 3.11 [#2801](https://github.com/demisto/demisto-sdk/pull/2801)
* Added validation for image files in doc_files folder. [#4249](https://github.com/demisto/demisto-sdk/pull/4249)
* Refactored PB101 and PB123 valildations. [#4273](https://github.com/demisto/demisto-sdk/pull/4273)
* Refactored validation IF116, Check whether a selectValue key in an incidentField of type multiSelect contains empty options. [#4278](https://github.com/demisto/demisto-sdk/pull/4278)
* Added support for IT valildations in the new validation command. [#4264](https://github.com/demisto/demisto-sdk/pull/4264)
* Converted the RM106 validation to the new format. The validation verifies that README doesn't contain the word 'demisto'. [#4295](https://github.com/demisto/demisto-sdk/pull/4295)
* Converted the DS107 validation to the new format. The validation verifies the integration description doesn't contain the word 'demisto'. [#4296](https://github.com/demisto/demisto-sdk/pull/4296)
* Added XSIAM prefix for the `defaultDataSource` integration README. [#4305](https://github.com/demisto/demisto-sdk/pull/4305)
* When updating an existing graph, the list of updated packs is now sorted. [#4261](https://github.com/demisto/demisto-sdk/pull/4261)
* Refactored all DA valildations. [#4264](https://github.com/demisto/demisto-sdk/pull/4264)
* Updated validation BC106, Verify that the fromVersion key in an incident field has not been changed. [#4276](https://github.com/demisto/demisto-sdk/pull/4276)
* Refactored validation DS100, check whether a description file exists for a beta integration. [#4274](https://github.com/demisto/demisto-sdk/pull/4274)
* Removed support for the `defaultDataSource` field in the pack metadata for hybrid packs. [#4302](https://github.com/demisto/demisto-sdk/pull/4302)
* Refactored validation IM111, Verify the integration image is within the allowed dimensions. [#4255](https://github.com/demisto/demisto-sdk/pull/4255)
* Added the `defaultDataSource` field to the pack metadata. [#4139](https://github.com/demisto/demisto-sdk/pull/4139)
* Change the default `fromversion` of XSIAM content items to 8.0.0 [#4243](https://github.com/demisto/demisto-sdk/pull/4243)
* Fixed an issue where `.demisto-sdk-conf` did not take into consideration command arguments setting to `false`. [#4253](https://github.com/demisto/demisto-sdk/pull/4253)
* Fixed an issue where **format** did not take `.demisto-sdk-conf` into consideration. [#4253](https://github.com/demisto/demisto-sdk/pull/4253)
* More detailed error message with action items for validation RM108. [#4269](https://github.com/demisto/demisto-sdk/pull/4269)
* Removed lint step from all sdk build steps. [#4286](https://github.com/demisto/demisto-sdk/pull/4286)

## 1.29.3
* Fixed an issue where **validate** ran from-version validation on `trigger` content items which do not have *from_version* field. [#4235](https://github.com/demisto/demisto-sdk/pull/4235)
* Fixed an issue where requests to dockerhub failed on rate-limits when authenticating with username and password. [#4227](https://github.com/demisto/demisto-sdk/pull/4227)
* Fixed an issue where reading **pre-commit** config templates would not handle cases with key=false and key:mode=true. [#4238](https://github.com/demisto/demisto-sdk/pull/4238)
* Improved printing of file paths in the internal gitutil. [#4251](https://github.com/demisto/demisto-sdk/pull/4251)

## 1.29.2
* Added the `--docker_image` and `--image_ref` flags to **pre-commit* to override values from configuration files. [#4223](https://github.com/demisto/demisto-sdk/pull/4223)
* Removed the `update-additional-dependencies` script and pre-commit hook. [#4225](https://github.com/demisto/demisto-sdk/pull/4225)

## 1.29.1
* Fix metadata (i.e. description) for XSOAR6 marketplace. [#4208](https://github.com/demisto/demisto-sdk/pull/4208)
* Fixed an issue where `xsoar_on_prem` tag, was not removed as part of the parsing process. [#4218](https://github.com/demisto/demisto-sdk/pull/4218)
* Added support to delete packs in **graph update** [#4205](https://github.com/demisto/demisto-sdk/pull/4205)
* Added a default `.pre-commit-config_template.yaml` file that will be used by **pre-commit** command in case such does not exist in the target repository. [#4194](https://github.com/demisto/demisto-sdk/pull/4194)
* Fixed an issue where the graph was not fully cleaned before import in **graph update** [#4215](https://github.com/demisto/demisto-sdk/pull/4215)
* Fixed an issue where tests were not collected in VSCode after **setup-env** [#4219](https://github.com/demisto/demisto-sdk/pull/4219)
* Fixed an issue where validate spammed logs when running. [#4203](https://github.com/demisto/demisto-sdk/pull/4203)
* Added the **dump-api** command to dump the demisto-sdk API to a JSON file. [#4214](https://github.com/demisto/demisto-sdk/pull/4214)

## 1.29.0
* The new validate flow is enabled by default while the old one is disabled. If you want to change this behavior, use the **--run-old-validate** and **--skip-new-validate** flags or the **RUN_OLD_VALIDATE** and **SKIP_NEW_VALIDATE** environment variables. [#4114](https://github.com/demisto/demisto-sdk/pull/4114)
* A new version of validate is available. For more information, refer to the readme. (a docs web page with further information about each validation will be added soon). Note that the old validate flow is beginning to go under a deprecation process and will eventually be removed. [#4114](https://github.com/demisto/demisto-sdk/pull/4114)
* Added the `--template-path` argument to the **pre-commit** command. [#4184](https://github.com/demisto/demisto-sdk/pull/4184)
* Added support for a new argument **parallel* for each hook to determine whether a hook run in parallel or not. [#4130](https://github.com/demisto/demisto-sdk/pull/4130)
* Added handling for API Modules in **pre-commit**. [#4175](https://github.com/demisto/demisto-sdk/pull/4175)
* Fixed an issue in **pre-commit** when using `--all-files` it crashed with memory error. [#4196](https://github.com/demisto/demisto-sdk/pull/4196)
* Fixed an issue in **graph update** where all content packs were being parsed. [#4186](https://github.com/demisto/demisto-sdk/pull/4186)
* Fixed an issue in **graph update** to create the graph from scratch if changed packs can not be determined. [#4186](https://github.com/demisto/demisto-sdk/pull/4186)
* Fixed an issue in **graph update** where the graph failed to update in external repositories. [#4190](https://github.com/demisto/demisto-sdk/pull/4190)
* Fixed an issue where **pre-commit** command showed wrong hooks failing. [#4130](https://github.com/demisto/demisto-sdk/pull/4130)
* Fixes an issue where *Fetch Events* and *Fetch Assets* checkboxes appeared in Xsoar Machines. [#4160](https://github.com/demisto/demisto-sdk/pull/4160)
* Added an implicit validation for the graph's *relationship* object by converting it to utilize Pydantic. [#4142](https://github.com/demisto/demisto-sdk/pull/4142)

## 1.28.0
* Added the `validate-xsoar-config` pre-commit hook, replacing `XC` validations. [#4150](https://github.com/demisto/demisto-sdk/pull/4150)
* Add `--prev-version` argument to **pre-commit** command. [#4177](https://github.com/demisto/demisto-sdk/pull/4177)
* Installing virtual environment in **setup-env** command will use `uv` and will fall back to `pip` to install requirements. [#4065](https://github.com/demisto/demisto-sdk/pull/4065)
* Fixed an issue where **pre-commit** failed when called from an inner directory of a content repo. [#4182](https://github.com/demisto/demisto-sdk/pull/4182)
* Fixed an issue where **generate-docs** command didn't work on newly-created integrations in existing Packs. [#4162](https://github.com/demisto/demisto-sdk/pull/4162)
* Fixed an issue in **setup-env** where the pack was not uploaded correctly to XSOAR/XSIAM. [#4166](https://github.com/demisto/demisto-sdk/pull/4166)
* Fixed an issue in **setup-env** where debug failed when running locally and not with docker. [#4166](https://github.com/demisto/demisto-sdk/pull/4166)
* Added a script for generating validation docs [#4103](https://github.com/demisto/demisto-sdk/pull/4103)

## 1.27.5
* Added the `validate-content-path` **pre-commit** hook [#4084](https://github.com/demisto/demisto-sdk/pull/4084)
* Fixed an issue where **setup-env** command failed when demistomock.py file does not exist locally. [#4094](https://github.com/demisto/demisto-sdk/pull/4094)
* Fixed an issue where **prepare-content** command didn't add contribution section to description files when support level of pack-metadata was `developer` support. [#4151](https://github.com/demisto/demisto-sdk/pull/4151)
* Fixes an issue in **graph** commands where empty pack folders were not being ignored. [#4154](https://github.com/demisto/demisto-sdk/pull/4154)
* Update file paths in `test_content` from ec2-user to gcp-user. [#3828](https://github.com/demisto/demisto-sdk/pull/3828)

## 1.27.4
* Added support for `run_isolated` field to the **pre-commit** configuration file. [#3952](https://github.com/demisto/demisto-sdk/pull/3952)
* Added support for `pass_docker_extra_args` field to the **pre-commit** configuration file. [#3952](https://github.com/demisto/demisto-sdk/pull/3952)
* Added the `auto_update_docker_image` field to the content-graph for scripts and integrations. [#4133](https://github.com/demisto/demisto-sdk/pull/4133)
* Fixed an issue in **validate** where several failed silently when the readme was malformed and the validation was ignored in the pack ignore errors. [#4129](https://github.com/demisto/demisto-sdk/pull/4129)

## 1.27.3
* Fixed an issue in **lint** and **pre-commit** with custom container registry [#4039](https://github.com/demisto/demisto-sdk/pull/4039)

## 1.27.2
* Updated the *DO106* error code in the **validate** command to not fail when a docker image is younger than 3 months instead of 3 days. [#4119](https://github.com/demisto/demisto-sdk/pull/4119)
* Fixed an issue where **lint** crashed when collecting invalid logs. [#4072](https://github.com/demisto/demisto-sdk/pull/4072)
* Adds auto-update to existing integration README and fixes README generation for existing Packs in contribution flow. [#3820](https://github.com/demisto/demisto-sdk/pull/3820)
* Fixed an issue where new release notes were generated without marketplace specific tags when needed. [#4118](https://github.com/demisto/demisto-sdk/pull/4118)
* Improved reviewer instructions on outdated pack submissions. [#4113](https://github.com/demisto/demisto-sdk/pull/4113)

## 1.27.1
* Updated the **validate** command (`PA114`) to verify the "currentVersion" field was raised in the pack_metadata when changing specific fields in the pack_metadata file. [#3972](https://github.com/demisto/demisto-sdk/pull/3972)
* Added support for **update-release-notes** command to update release notes when changing specific fields in the pack_metadata file. [#3972](https://github.com/demisto/demisto-sdk/pull/3972)
* Added support to load the correct file content when reading remote files according to its URL. [#4050](https://github.com/demisto/demisto-sdk/pull/4050)
* Added to the **pre-commit** command a new hook `validate-deleted-files` which validates it is not possible to delete certain files. [#4050](https://github.com/demisto/demisto-sdk/pull/4050)
* Added support for `hybrid` field in pack_metadata.json and the integration YAML. [#4087](https://github.com/demisto/demisto-sdk/pull/4087)
* Improved error handling when reading files locally, remotely or from git. [#4081](https://github.com/demisto/demisto-sdk/pull/4081)
* Added README to the **xsoar-lint** command [#4043](https://github.com/demisto/demisto-sdk/pull/4043)
* Fixed an issue where SDK would crash when running on repoitories which do not have git configured. [#4088](https://github.com/demisto/demisto-sdk/pull/4088)
* Fixed an issue where reading files on repositories which are not git repositories failed when the path provided was relative path. [#4088](https://github.com/demisto/demisto-sdk/pull/4088)
* Fixed an issue where **lint** would crash without internet connectivity. [#4098](https://github.com/demisto/demisto-sdk/pull/4098)
* Fixed an issue where SDK would crash when trying to read files which are not encoded with utf-8 directly from memory. [#4081](https://github.com/demisto/demisto-sdk/pull/4081)
* Added description field to *Assets Modeling Rules* content item. [#4005](https://github.com/demisto/demisto-sdk/pull/4005)
* Added the `validate-conf-json` pre-commit hook, checking for structure and linked content. [#4051](https://github.com/demisto/demisto-sdk/pull/4051)

## 1.27.0
* Added the **graph get-dependencies** command. [#3992](https://github.com/demisto/demisto-sdk/pull/3992)
* Added a new command **xsoar-lint** and added it as a hook to **pre-commit**. [#3962](https://github.com/demisto/demisto-sdk/pull/3962)
* Fixed an issue where **lint** created containers with the same name leading the command to crash. [#4019](https://github.com/demisto/demisto-sdk/pull/4019)
* Fixed an issue where **secrets** command failed in case of detached head git state [#4041](https://github.com/demisto/demisto-sdk/pull/4041)
* Fixed an issue where a few USES relationships between playbooks were not collected by the playbook parser. [#4032](https://github.com/demisto/demisto-sdk/pull/4032)
* Fixed an issue where *validate* failed *pre-processing rule* id-set file validation. [#4042](https://github.com/demisto/demisto-sdk/pull/4042)
* Fixed an issue where **validate** would not mention the reason when failing to connect to MDX. [#4048](https://github.com/demisto/demisto-sdk/pull/4048)
* Fixed an issue where reading files from git could not be read when a commit did not exist locally. [#4052](https://github.com/demisto/demisto-sdk/pull/4052)
* Fixed an issue where the **upload** command failed when using the `DEMISTO_SDK_OFFLINE_ENV` environment variable. [#4034](https://github.com/demisto/demisto-sdk/pull/4034)
* Fixed an issue where **setup-env** crashed when trying to upload an instance of an integration into xsoar. [#4044](https://github.com/demisto/demisto-sdk/pull/4044)
* Fixed an issue where the *init* command sometimes failed in the dialogue when enter was pressed and not explicitly written false. [#4058](https://github.com/demisto/demisto-sdk/pull/4058)
* Fixed an issue where validate would state that it failed, even though it shouldn't, and then it would display an empty list of content items when running on specific validations. [#4006](https://github.com/demisto/demisto-sdk/pull/4006)
* Fixed an issue where reading files from git failed when sending file paths as absolute. [#4060](https://github.com/demisto/demisto-sdk/pull/4060)
* Code readability improvements in the **error-code** command. [#3322](https://github.com/demisto/demisto-sdk/pull/3322)
* Update `update_content_graph` function to create the graph from scratch if `DEMISTO_SDK_GRAPH_FORCE_CREATE` env is set to true. [#4037](https://github.com/demisto/demisto-sdk/pull/4037)
* Updated the path of the `neo4j` directory, generated & used by the `graph` commands, to project's directory (`$HOME/.demisto-sdk`). [#4010](https://github.com/demisto/demisto-sdk/pull/4010)
* Added a `DEMISTO_SDK_NEO4J_VERSION` environment variable to set a custom Docker tag to pull for the `neo4j` image instead of the default one. [#4010](https://github.com/demisto/demisto-sdk/pull/4010)
* Added `comment:marketplacev2` to the script schema. [#4077](https://github.com/demisto/demisto-sdk/pull/4077)
* Sped up the way **validate** checks for deprecated content items. [#3578](https://github.com/demisto/demisto-sdk/pull/3578)
* Sped up the way **validate** reads pack_metadata.json files. [#3578](https://github.com/demisto/demisto-sdk/pull/3578)
* Added support for SVG image files in the **validate** command. [#4047](https://github.com/demisto/demisto-sdk/pull/4047)
* Added support to set `deprecated` field for specific marketplaces in content items. [#4078](https://github.com/demisto/demisto-sdk/pull/4078)
* Added a new step in the **validate-changelog** to comment the changelog description in PR comments. [#4040](https://github.com/demisto/demisto-sdk/pull/4040)
* Added support to query the pull request number automatically when running **sdk-changelog --init** command. [#4040](https://github.com/demisto/demisto-sdk/pull/4040)
* Modified the logging level of a few messages accross the SDK. [#3301](https://github.com/demisto/demisto-sdk/pull/3301)

## 1.26.2
* Added support to check the health status when initialing a client for xsoar-on-prem/xsoar-saas by default, will throw exception if server is not healthy. [#3985](https://github.com/demisto/demisto-sdk/pull/3985)
* The `create-content-graph` command is now deprecated and will be removed in future releases. Use the `demisto-sdk graph create` command instead. [#4027](https://github.com/demisto/demisto-sdk/pull/4027)
* The `update-content-graph` command is now deprecated and will be removed in future releases. Use the `demisto-sdk graph update` command instead. [#4027](https://github.com/demisto/demisto-sdk/pull/4027)
* Fixed an issue where downloading custom content items with special YAML characters (like `:`) in their names would cause an error during UUID ID replacement when using the **download** command. [#3990](https://github.com/demisto/demisto-sdk/pull/3990)
* Fixed an issue where **validate** failed on _data.json, when saved in a folder under `Lists` (rather than directly under `Lists`). [#3997](https://github.com/demisto/demisto-sdk/pull/3997)
* Fixed an issue where the **pre-commit** pycln hook failed when the repo name contained hypens. [#3998](https://github.com/demisto/demisto-sdk/pull/3998)
* Fixed an issue with **prepare-content** where partner event collectors which are supported by PANW add irrelevant suffixes to their display names. [#4021](https://github.com/demisto/demisto-sdk/pull/4021)
* Fixed an issue in **setup-environment** command where `.env` files were not loaded correctly. [#4029](https://github.com/demisto/demisto-sdk/pull/4029)
* Fixed an issue where **upload** failed when trying to upload a content item that was missing a *description* or *type* fields. [#4020](https://github.com/demisto/demisto-sdk/pull/4020)
* Update the lock_integrations in **test-content** command to check if the current job still running (and not the pipeline). [#4016](https://github.com/demisto/demisto-sdk/pull/4016)
* Fixed an issue where some unit-tests failed in github-actions CI. [#4023](https://github.com/demisto/demisto-sdk/pull/4023)

## 1.26.1
* Added retry mechanism for create docker container. As default, will attempt three times. [#3988](https://github.com/demisto/demisto-sdk/pull/3988)
* Fixed the init command to successfully create event collector integration [#3995](https://github.com/demisto/demisto-sdk/pull/3995)
* Fixes an issue where running **pre-commit** with the `run-hook` argument didn't execute the hook in some cases. [#3999](https://github.com/demisto/demisto-sdk/pull/3999)
* Fixed an issue where fetching from a git remote would cause a failure in cases where fetching is not necessary. [#3878](https://github.com/demisto/demisto-sdk/pull/3878)
* Added support for DOCKER_REGISTRY_URL environment variable. [#3975](https://github.com/demisto/demisto-sdk/pull/3975)

## 1.26.0
* Log file path (can be set by the `--log-file-path` flag or the `DEMISTO_SDK_LOG_FILE_PATH` environment variable) can now only accept directory values. Setting it to a file path is no longer supported (file name is now constantly `demisto_sdk_debug.log` and cannot be changed). The path will now be automatically generated if it doesn't exist. [#3912](https://github.com/demisto/demisto-sdk/pull/3912)
* Log files will now be saved by default to `$HOME/.demisto-sdk/logs`. This behavior can be overridden by the `--log-file-path` flag, or the `DEMISTO_SDK_LOG_FILE_PATH` environment variable. [#3912](https://github.com/demisto/demisto-sdk/pull/3912)
* Added warning when running on Windows (not supported) [#3950](https://github.com/demisto/demisto-sdk/pull/3950)
* Fixed an issue where the ***validate*** command failed on pre-processing rules. [#3977](https://github.com/demisto/demisto-sdk/pull/3977)
* Fixed an issue in **upload** where customFields with explicitly defined values (e.g., ${}) caused the command to fail. [#3970](https://github.com/demisto/demisto-sdk/pull/3970)
* Fixed an issue where validate command failed with Lists folder containing a data json file. [#3971](https://github.com/demisto/demisto-sdk/pull/3971)
* Added graph capabilities in **TestSuite**. [#3932](https://github.com/demisto/demisto-sdk/pull/3932)

## 1.25.3
* Fixed false positives in **validate** in `GR103` validations [#3873](https://github.com/demisto/demisto-sdk/pull/3873)
* Add command `sdk-changelog` for creating a yml file to describe the development changes in the SDK [#3177](https://github.com/demisto/demisto-sdk/pull/3177)
* Locking the `CHANGELOG.md` file for changes when the PR is not a release process [#3177](https://github.com/demisto/demisto-sdk/pull/3177)

## 1.25.2
* Fixed an issue in the **prepare-content** and the **upload** commands where the unified YAML/JSON file was parsed instead of the original file.
* Fixed an issue where **lint** command didn't work on detached heads.
* Added the *DockerHubClient* class to allow interaction with the dockerhub-api efficiency and easily.
* Added support to check the version of the modeling rule against the demisto version of the XSIAM tenant when running the **modeling-rule test** command, and skip incompatible modeling rules.
* Added support for JetBrains IDEs (PyCharm, IDEA, etc.) to the **setup-env** command, and added a new `--ide` flag.
* Internal: Fixed an issue where `nativeimage` tags were not uploaded to buckets.
* Fixed an issue where **lint -g** crashed when comparing changes against branches which are not `master`.
* Fixed an issue in **prepare-content** command where the `incident to alert` process was not triggered when the playbook is set to only XSIAM.
* Fixed an issue where **validate -g** command crashed when comparing changes against branches when in detached head state.
* Add support for tests to run on specified marketplaces.

## 1.25.1
* Added the `clean` flag to **setup-env** to delete temp files that were created by `lint` from the repo.
* Fixed an issue in **validate** where there is a specific value for marketplace in `isFetch` parameter.
* Fixed an issue where the build number was incorrectly shown in XSOAR marketplace when using the **upload** command on external repositories via GitLab Pipelines.
* Added support for `excluding_support_level` property in **pre-commit** command to exclude specific support level from running hooks.
* Added support for the `List` content-item to **prepare-content** and **split**.
* **Breaking change**: The **download** command will no longer download the content-item `List` in a unified file but instead will split the content-item `List` into two files (metadata and data).
* Fixed an issue in **generate-docs** where the description field was missing from an argument.
* Changed the log level of some **pre-commit** `DockerHook` messages from `info` to `debug`.

## 1.25.0
* Added support to detect automatically the playground-id when running cli commands in xsoar-6.
* Added support to return war-room entries when running cli commands.
* Added support to automatically detect the correct file model by file path when reading files.
* Fixed an issue where **run-playbook** command didn't work if the *url* argument was not provided.
* Fixed an issue where **validate** command failed on valid complex layout rules and triggers.
* Fixed an issue where *validate* command failed with release notes files for assets modeling rules folder.
* Added support for `skip` property in **pre-commit** hooks.
* **generate-unit-tests** command will require installation with `pip install demisto-sdk[generate-unit-tests]`.
* Added the *IN150* and *IN161* errors to *allowed ignore errors* list.
* Added support for `env`, `copy_files` property in **pre-commit** docker hooks.
* Added support to run specific hooks in **pre-commit**. Use with `demisto-sdk pre-commit <hook>`.
* **Breaking change**: Removed the command **run-unit-tests**. Use `demisto-sdk pre-commit pytest-in-docker` instead.
* **Breaking change**: Removed the `--unit-test` argument in **pre-commit**. To skip unit tests, run with `--no-docker` or with `skip=pytest-in-docker`,
* Fixed an issue where SDK commands were failing to execute correctly when supplied a path outside the Content repository.

## 1.24.0
* Fixed an issue where the error was not clear when trying to retrieve the server version.
* Fixed an issue in **prepare-content** where tags were added to metadata because of test scripts.
* Fixed an issue in **coverage-analyze** to exit gracefully in case that the .coverage file doesn't exist.
* Breaking change: **ValidateManager** was renamed to **OldValidateManager** and can now be found at the following [path](demisto_sdk/commands/validate/old_validate_manager.py).
* Fixed an issue where to_id_set_entity method failed on id extraction due to missing pack.
* Fixed an issue where **run-playbook** command did not work.
* Fixed an issue in **setup-env** command where the virtual environment failed to set up.
* Fixed an issue in **pre-commit** command where `False` properties were deleted.
* Added support for json5 file, allowing to write files and read files from specific git branches, local file system, or from any remote api .
* Fixed an issue in **upload** command where the `marketplace` field was not taken into consideration when uploading single content-items.
* Added support for *Assets Modeling Rule* new content item in all `demisto-sdk` commands.

## 1.23.0
* Added support for inputs sections and outputs sections in a playbook.
* Added a new service for file management, allowing to write files and read files from specific git branches, local file system, or from any remote api.
* Added a new flag `--docker/--no-docker` to demisto-sdk pre-commit, in order to enable the option to run the pre-commit command without docker hooks.
* Added support for xsoar, xsoar-saas and xsiam wrapper clients to ease the integration via their apis.
* Added the command demisto-sdk coverage-analyze to the pre-commit hooks.
* Updated merge_coverage_report to be a hook in the pre-commit.
* Updated the mode option to be free text. for more details see https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/pre_commit/README.md#modes
* Added a new command **setup-env** to setup the environment for integrations and scripts in vs code IDE, XSOAR and XSIAM.
* Fixed an issue where the SDK failed to retrieve docker hub token when there were temporary connection errors.
* Internal: Added a welcome comment to contributions PRs.
* Fixed metadata dependencies dumping in **prepare-content** command.
* Fixed an issue where the TagParser didn't work properly on all edge cases.

## 1.22.0
* Added Docker Hook support to **pre-commit**; for details see https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/pre_commit/README.md#docker-hooks
* Removed **-use-local-import** flag to **graph update** command.
* Perfomance improvements to **graph** commands.
* Adjust graph structure to accommodate anticipated changes in infrastructure for the **validate** command.
* Fixed an issue where the **lint** command with docker, would not give unique container names to different image runs.
* Added a new `display_name` field to `Pack` entity in graph.

## 1.21.0
* Added the argument `--commited-only` to **pre-commit** to skip collecting on staged files.
* Fixed an issue where the **pre-commit** command runs even in the case of deprecated or powershell integrations or scripts.
* Fixed an issue where **validate** falsely failed with error `PB101` and `PB123` due to condition names discrepancy
* Fixed an issue where the **modeling-rules test** command failed report and error when test data didn't exist.
* Changed the table print for **modeling-rules test** command.
* Updated the **prepare-content** to add contributor details to the `detaileddescription` field based on **supportlevelheader** key.
* Added a new validation (`IN162`) to ensure that each event collector under partner supported packs have the *xsoar* value for the **supportlevelheader** key in its yml.
* A rewrite for the **download** command, with many improvements and fixes, including:
  * Large optimizations: reducing the runtime and CPU usage by a significant amount when there's a considerable amount of custom content items on the server.
  * Improved error handling and messages, logs, and documentation (`demisto-sdk download --help`) for the command.
  * Fixed an issue where custom PowerShell-based integrations and automations would not download properly.
  * Fixed an issue where names of the following custom content items would not have their IDs replaced from UUIDs:
    * Classifiers
    * Dashboards
    * Indicator Types
    * Reports
    * Widgets
  * Fixed an issue where the download would fail when using the '-r' / '--regex' flag when there were multiple custom content items on the server matching the pattern, having the same name.
  * Fixed an issue where integrations / automations with a dot in their name would be saved with an incorrect file name (For example: `Test v1.1.py` would be named `Test v1.py`)
  * Fixed the **Link to Jira** Github flow to match the Jira-dc.

**Note:** Due to the optimization changes made to the **download** command, playbooks might be formatted a bit differently than before when downloaded from the server using the new version. The playbooks should however function and work the same.
* Fixed an issue where the **pre-commit** command, now correctly gathers the associated python file when a yml file is provided as input.
* Internal: Added a new GitHub action that will automatically assign the contribution TL and add the `Contribution` label in contributions PRs.

## 1.20.8
* Internal: Fixed an issue where the `tools.get_id` function would not find the ID for layout content items in some cases.
* Internal: Fixed an issue where the `tools.get_display_name` function would return incorrect values for "Indicator Type" content items.
* Changed the error code of the **validate** check for deprecated display names from `IN157` (duplicated a code used by a `nativeimage` check) to `IN160` (new code).
* Changed the error code of the **validate** check for invalid SIEM marketplace values from `IN151` (duplicated a code used by a check for empty command arguments) to `IN161` (new code).
* Added JUnit XML output support for **test-content** command.
* Updated the **run-unit-tests** command to not fail on JavaScript items, but skip them instead.
* Updated the `validate` pre-commit hook to run before the `run-unit-tests` hook. This will prevent `validate` from falling on errors about temporary files that are sometimes created when running unit-tests.
* Added the *auto-replace-uuids* flag to the **download** command. set this flag to False to avoid UUID replacements when downloading using download command.
* Added a new key **supportlevelheader** to the integration schema.
* **format** command will run without the content graph if graph creation fails.
* Updated the `GENERAL_DEFAULT_FROMVERSION` variable from **6.9.0** to **6.10.0**.
* Internal: Replaced the `tools._read_file` function with a more generic `tools.safe_read_unicode` function.
* Internal: Added `pathlib.Path` support to the `tools.get_yml_paths_in_dir` and `tools.get_child_directories` functions.
* Fixed an issue in the **test-modeling-rule** command, where possible exceptions were not caught.
* Added the *--delete_existing_dataset/-dd* flag to the **modeling-rules test** command to delete an existing dataset in the tenant.
* Added a new validation (`IN159`) which validates that reputation commands context outputs are spelled according to standards.
* Internal: Added a `loaded_data` parameter to `YmlSplitter` to allow passing preloaded YAML data.

## 1.20.7
* Fixed an issue where unified integrations / scripts with a period in their name would not split properly.
* Fixed an issue where the documentation was out of date with the current structure of **demisto-sdk** which does not support command auto-completion.
* Improved logging for **lint** and **prepare-content** commands.
* Internal: Added the `CI_SERVER_HOST`, `CI_PROJECT_ID` environment variables.

## 1.20.6
* Added the *--mode* argument to the **pre-commit** command, to run pre-commit with special mode (to run with different settings), supported mode are: 'nightly'.
* Modified the `validate` and `format` pre-commit hooks to run with the `--all` flag only when the `--mode=nightly` argument and `--all` flag were given.
* Modified the `ruff` pre-commit hook to run with `--config=nightly_ruff.toml` argument when running **pre-commit** command wite the `--mode=nightly` argument.
* Fixed an issue where deprecating parsing rules or modeling rules using **format** failed due to schema discrepancies.
* Fixed an issue where kebab-case arguments were not parsed correctly.
* Fixed an issue where **validate** falsely failed with error `RN115` on release notes with linefeed at the end of the file.
* Fixed an issue where **validate** falsely failed with error `DS108` on descriptions ending with new lines followed by square/curly brackets.
* Fixed an issue where **graph** commands would not clean their temporary files properly, causing successive commands to fail.
* Fixed an issue where an error log message changed the terminal color.

## 1.20.5
* Fixed an issue where **validate** falsely failed with error `DS108` on descriptions ending with brackets that contains a dot at the end of them.
* Fixed an issue where **modeling-rule test** command failed to properly render the comparison table when boolean value were printed.
* Fixed an issue were format added a dot at end of the description that already ends with question mark and exclamation mark.
* Fixed an issue where **upload** failed when trying to upload an indicator field.
* Updated the **update-content-graph** command to work with external repositories.
* Updated the **validate** command to work with external repositories when using the *--graph* flag.
* added support for `isfetchassets` flag in content graph

## 1.20.4
* Fixed an issue where using **prepare-content**, **upload**, **zip-packs** and **download** on machines with default encoding other than unicode caused errors.
* The **modeling-rules-test** will now ignore test data files containing the `test_data_config_ignore` key.
* Fixed an issue where **modeling-rules init-test-data** command failed on modeling rules that contain the text `call` even not as a separate word.
* Unlocked the dependency on `packaging`.

## 1.20.3
* Added the `FileType.VULTURE_WHITELIST` to the `FileType` enum for `.vulture_whitelist.py` files.
* Improved performance when reading `yml` files.
* Fixed an issue where **format** would add unnecessary period at the end of descriptions ending with brackets.
* Fixed an issue where **format** would not add a period at the end of descriptions, when running on in script files.
* Fixed an issue where running **validate -g** failed reading a `.pack-ignore` file that contained only newlines and spaces.
* Fixed an issue where **upload** failed when trying to upload a list content item.
* Fixed an issue where **download** would skip downloading list content items assigned to specific user roles with no roles.
* Demisto-SDK will now exit gracefully with an appropriate error message when *git* is not installed.
* Updated validation *RN116* to support the structure of **--force** flag in *update-release-notes* command.
* Fixed an issue where the release notes file was not added automatically to git when using the *update-release-notes* command.
* Fixed the structure in *update-release-notes* command when used with the **--force** flag. Now the header will display the pack display name.
* Fixed the support in **validate** for `svg` images to have their theme suffix.
* Modified **validate** to support only .svg files ending with *_dark* or *_light* suffixes.
* Fixed an issue where **modeling-rule test** command failed to properly compare types of fields.
* Fixed an issue where **validate** falsely failed with error `DS108` on descriptions ending with question mark and exclamation mark.
* Updated the **engineinfo** type in the script schema.
* Updated the **modeling-rules init & test** commands to support RULE section fields.
* Stability improvements for **graph create** and **graph update** commands.
* Fixed the *metadata* type in the XSIAM dashboard schema to *map*, with possible values: **lazy_load** and **cache_ttl**

## 1.20.2
* Updated the **pre-commit** command to run on all python versions in one run.
* Added the *--dry-run* flag to the **pre-commit** command, to create the config file without running the command.
* Fixed an issue where the **coverage-analyze** command was not parsing the logs correctly.
* Fixed an issue where **validate** falsly failed with error `DS108` on descriptions ending with a newline.
* Added formatting for script yml files when period is missing in the end of comment field, in the **format** command.
* Fixed an issue where **format** add a newline with a period when the description field missing a period.
* The content graph will now include the **python_version** field that each script/integration uses.
* Updated the **update-release-notes** command message structure when is run with **--force** flag.
* Added the **engineinfo** in to the script schema. This field specifies on which engine the script will run.
* Fixed an issue where **validate** falsely failed with error `DS108` on empty descriptions.
* Added support for lazy loading the of widgets in XSIAM dashboards.
* Added a **validate** check for correlation rules, making sure that `search_window` cannot be empty when `execution_mode` is set to `SCHEDULED`.
* Added the *metadata* key to the XSIAM dashboard schema. This field adds support for dynamic parameters in the dashboards.

## 1.20.1
* Added formatting for yml files when period is missing in the end of description field, in the **format** command.
* Fixed an issue where logging arguments were not in the standard kebab-case. The new arguments are: **console-log-threshold**, **file-log-threshold**, **log-file-path**.
* Added a new validation (`DS108`) to ensure that each description in the yml of script/integration ends with a dot.
* Fixed an issue where the **validate -g** failed reading a `.pack-ignore` file that was previously empty.
* Fixed an issue where the **update-release-notes** failed when changing the `.pack-ignore` file.
* Fixed an issue where the **GR103** validation output was malformed.
* Fixed an issue where the **upload** command failed for private repositories while trying to find the landing_page.json file.
* Added a log when a content item is missing from the repo, in **graph create** and **graph update**.
* Replaced logs with a progress bar in **graph create** and **graph update**.


## 1.20.0
* Fixed an issue where **update-release-notes** generated "available from Cortex XSOAR" instead of "from XSIAM" when run on XSIAM event collectors.
* Added support for controlling the sleep interval and retry count for **modeling-rules test** command.
* Added support for a new marketplace tag `xsoar_saas`.
* Fixed an issue where the **validate -g** failed on `BA102` in external repos even when ignored.
* Fixed an issue where the **validate -g** failed getting the content of `.pack-ignore` files when the external repository is not hosted in Github.
* Fixed an issue where the **validate -g** failed when updating an empty `.pack-ignore` file.
* Added support for yml hidden parameters for `xsoar_saas` marketplace, as part of the **prepare_content** command.
* Added support for custom documentation that will appear only in `xsoar_saas` marketplace, as part of the **prepare_content** command.
* Fixed an issue where the (`GR108`) validation did not fail in the validate command with the `-a` flag.
* Modified **prepare_content** command to be platform specific. For xsoar-saas and XSIAM regarding pack readme and integration description images in markdown files.
* Fixed an issue where the **lint** command was parsing % that may exist in the log data.

## 1.19.2
* Added a period at the end of lines produced by the **generate-docs** command that state the tested version of the product.
* Added the '--junit-path' flag to the **modeling-rules test** command, to allow saving the test results in a JUnit XML file.
* Update `RN112` validation's docs reference link.
* Added support to control the maximum file size and log rotation files count in the sdk logger.
* Fixed an issue with where passing the deprecated logging arguments to any command presented an incorrect recommendation for argument substitution.
* Fixed an issue where the documentation of logging arguments was incorrect.
* Fixed an issue in calculating content graph hash when creating or updating it.
* Fixed an issue where the coloring of the logging messages was not working properly when mixing both Console log and Parallel log handlers.
* Calling **graph create** or **graph update** now run the commands with default arguments, instead of showing the command help.
* Removed the use of chunks when calculating content relationships.
* Added the new environment variables **DEMISTO_DEFAULT_REMOTE** and **DEMISTO_DEFAULT_BRANCH**.
* Fixed an issue where the url regex in the **validate** command was wrong.
* Fixed an issue where **pre-commit** command failed when using global environment.
* Fixed an issue where **validate** would fail in external repos when trying to ignore `BA102`.
* Fixed an issue where **error-code** failed on some error codes.
* Fixes an issue in **format** command where the `-i` option included files in `.venv` directories.
* Updated the comment added to contribution PRs to old packs so it contains a link to the documentation of the **GitHub Codespaces** in xsoar.pan.dev.
* Updated GitPython version to 3.1.32.

## 1.19.1
* Fixed an issue where **unify** failed on integrations using an API a module, when not called from the content root.
* Improved **update-release-notes** logs when changes in dependent API modules are detected.
* Reverted changes released in version 1.19.0 in lint, lint will not fail on `demisto.results`, `return_outputs` and `LOG`.
* Updated the **generate-docs** command to use the content graph instead of the id_set file.
* **Validate** will now validate items which were edited in .pack-ignore.
* Added the '--all' input option for the **prepare-content** command, to support running on all content packs.
* Updated the '-i' input option of the **prepare-content** command to support multiple inputs as a comma-separated list.
* Enhanced the pack metadata properties when dumping pack zips in **prepare-content** command.

## 1.19.0
* Added the **graph** command group. The **create-content-graph** and **update-content-graph** commands were migrated to this command group, and named **graph create** and **graph update** respectively.
* Added the **graph get-relationships** command.
* The **graph create** command will now use a list of known content items from content-private, to avoid false-positives in validation `GR103`. Additionally, `GR103` was added to the **ALLOWED_IGNORE_ERRORS** list.
* The **modeling-rules test** command will now validate that the modeling rules schema mappings are aligned with the test-data mappings.
* Added the *--xsiam* flag to the **init** command in order to create XSIAM content.
* Fixed an issue where the `update-additional-dependencies` **pre-commit** step failed when not running in a content-like repo.
* Removed the format execution step from the `contribution_converter` since it can be executed separately during the contribution process.
* Added a new validation (`GR108`) to **validate**, that assures hidden packs do not have mandatory dependant packs.
* Added a new validation (`PA137`) to **validate**, ensuring the absence of non-ignorable errors in `.pack-ignore`.
* Running **validate** in a GitHub Action will now show errors as annotations, visible in the `Files Changed` tab of the pull request.
* **lint** will now fail on `demisto.results` and `return_outputs` usage, when a pack is `xsoar` or `partner` supported.
* **lint** will now fail on `LOG` usage in python files.
* Updated the **format** command to use the content graph instead of the id_set file.
* Updated **format** command not to fail on unexpected values that returns from the graph, and just add it to the log.
* Removed a redundant debug log on the `tools.get_file` function.

## 1.18.1
* Fixed an issue where the coloring directives where showing in log messages.
* Fixed an issue where **create-content-graph** was not executed upon changes in the parser infra files.
* Added support for `svg` integration images in content repo in **validate** command.
* Added a parameter `skip-packs-known-words` to the **doc-review** command, making sure that pack known words will not be added.

## 1.18.0
* Added the ability to ignore any validation in the **validate** command when running in an external (non-demisto/content) repo, by placing a `.private-repo-settings` file at its root.
* Calling **format** with the `-d` flag now removes test playbooks testing the deprecated content from conf.json.
* Improved the content graph performance when calculating content relationships.
* Improved determinism of SDK unit tests.
* **validate** will now run on all the pack content items when the pack supported marketplaces are modified.
* **pre-commit** no longer runs when there are no modified files (unless provided with input files).
* Added new validation that XSIAM integrations must have `marketplacev2` as the value of the marketplaces field.
* Added an ability to provide list of marketplace names as a credentials-type (type 9) param attribute.
* **doc-review** will run with the `--use-packs-known-words` true by default.
* Added the *deprecated* field to the pack object for the content-graph metadata.
* Calling **modeling-rules init-test-data** will now return the XDM fields output in alphabetical order.
* Added a new validation (`BA125`) to **validate**, assuring internal function names aren't used in customer-facing docs.
* Removed the Pipfile and Pipfile.lock from the templates in the **init** command.
* Disabled the option to create an integration with `Pipfile` and `Pipfile.lock` files, as they are deprecated.
* Added the Sourcery hook to **pre-commit**.
* Added a working directory to the `contribution_converter` in order to support working on a temporary directory.
* Added a waiting period when checking whether the dataset exists in the **modeling-rule test** command.
* Fixed an issue where the *DEMISTO_SDK_SKIP_VERSION_CHECK* was ignored when running on non CI environments.
* Fixed an issue where **validate** falsely detected backwards-compatibility issues, and prevented adding the `marketplaces` key to content items.
* Fixed an issue where the SDK would fail pulling docker images.
* Fixed an issue where **prepare-content** command would add the string `candidate` to scripts and integrations for the *nativeimage* key.
* Fixed an issue where in some cases the **split** command did not remove pack version note from the script.
* Fixed an issue where **validate** would not properly detect dependencies of core packs.
* Fixed an issue where **validate** failed on single-select types incident and indicator fields when given empty value as a select value option.
* Fixed an issue where errors in **validate** were logged as `info`.
* Fixed an issue where **validate** error messages were not logged when an integration param, or the default argument in reputation commands is not valid.
* Fixed an issue where the **format** command would change the value of the `unsearchable` key in fields.
* Fixed an issue where **lint** command failed to pull docker image in Gitlab environment.
* Fixed an issue in **doc-review** command where escape characters within Markdown files were detected as invalid words.
* Fixed an issue where **validate** failed on infrastructure test files.
* Fixed an issue in **update-content-graph** where the neo4j service was unaccessible for non-root users.

## 1.17.2
* Fixed an issue where **lint** and **validate** commands failed on integrations and scripts that use docker images that are not available in the Docker Hub but exist locally.
* Added documentation for the flag **override-existing** used in upload.
* Fixed an issue where **validate** failed on Incident Field items with a `template` value.
* Improved memory efficiency in **update-content-graph** and **create-content-graph** commands.
* Removed support for the `cve_id` name for the default-argument for **cve** reputation commands in **validate**. Now, only `cve` may be used for such commands.
* Fixed an issue where **zip_packs** failed uploading content.
* Added `tenant_timezone` handling to the **modeling-rules init** command, allowing usage with tenants in various timezones.
* Shortened the timeout when checking whether the dataset exists in **test-modeling-rule**.
* Cleaned up project dependencies.
* Added support for the **List** content item in **Xpanse** marketplace.
* Fixed an issue in **run-unit-tests** command when running Powershell tests.
* Fixed an issue where **lint** failed running when a docker container would not init properly.
* Fixed an issue where the *upload* command would upload a pack metadata with wrong display names.
* Performance enhancements when reading yaml files.
* Removed redundant errors and fields from `errors.py`.
* Updated **update-release-notes** to use graph instead of id_set.

## 1.17.1
* Added the `aliasTo` key to the Incident Field schema.
* Modified **validate** to not require fields whose value is always `False`.
* Modified **validate** to use the graph instead of id_set on changed *APIModules*.
* Fixed an issue where `register_module_line()` was not removed from python scripts when the script had no trailing newline.
* Fixed an issue where an integration containing a command without a description would fail to upload while using the **upload** command.
* Fixed an issue where attempting to individually upload `Preprocess Rule` files raised an unclear error message. Note: preprocess rules can not be individually uploaded, but only as part of a pack.
* Fixed an issue where the **upload** command would fail on Indicator Types.
* Fixed an issue where the **upload** command would return the wrong error message when connection credentials are invalid.
* Fixed an issue where the **upload** command would fail parsing input paths.
* added support for the `isfetcheventsandassets` flag in content graph.
* Fixed an issue where the **modeling-rules test** command failed to get the existence of result from dataset in cases where the results take time to load.
* Added an aliasTo key to the incident field schema.

## 1.17.0
* **validate** will only fail on docker related errors if the pack is supported by xsoar.
* Added a validation that assures filename, id, and name have a correct suffix for modeling/parsing rules files.
* Added new **validate** checks, preventing unwanted changes of the marketplaces (BC108,BC109), toversion (BC107)  and fromversion (BC106) fields.
* Removed the `timezone_offset` argument in the *modeling-rules test* command.
* Fixed an issue where **lint** failed when importing functions from CommonServerUserPython.
* The **format** command now will sync hidden parameters with master branch.
* Fixed an issue where lock integration failed on FileNotFound.(PANW-internal only).
* Fixed an issue where **lint** falsely warned of using `demisto.results`.
* Fixed an issue where **validate** always returned *XSIAM Dashboards* and *Correlation Rules* files as valid.
* Added `GR107` validation to **validate** using the graph validations to check that no deprecated items are used by non-deprecated content.
* Fixed an issue where the **modeling-rules test** command failed to get the existence of dataset in cases where the dataset takes more than 1 minute to get indexed.
* Fixed an issue in **lint** where the container used for linting had dependency conflicts with the image used by content, and caused inconsistent results.
* Fixed an issue where the **download** command failed when the playbook has different `name` and `id`.
* Moved the **pre-commmit** command template to the `demisto/content` repository, where it's easier to maintain.
* Fixed an issue where an internal method caused warning messages when reading md files.
* Added support for Pre Process Rules in the **upload** command.
* Fixed an issue where **upload** would not upload items whose `maketplaces` value was an empty list.
* Added a prettyName key to the incident field schema.
* Fixed an issue where **upload** command could not parse content items that are not unicode-encoded.

## 1.16.0
* Added a check to **is_docker_image_latest_tag** to only fail the validation on non-latest image tag when the current tag is older than 3 days.
* Fixed an issue where **upload** would not properly show the installed version in the UI.
* Fixed an issue where the `contribution_converter` failed replacing generated release notes with the contribution form release notes.
* Fixed an issue where an extra levelname was added to a logging message.
* Modified the `mypy` pre-commit hook to run in a virtual environment, rather than the local mypy version.
* Added support to run **validate** with `--git` flag on detached HEAD.
* Added a validation that the **validate** command will fail if the pack name is not prefixed on XSIAM dashboard images.
* Fixed the **generate-test-playbook** which failed on an unexpected keyword argument - 'console_log_threshold'.
* Fixed an issue where **prepare-content** would not properly parse the `fromVersion` and `toVersion` attributes of XSIAM-Dashbaord and XSIAM-Report content items.
* Fixed an issue where **validate** command did not fail on non-existent dependency ids of non-mandatory dependant content.
* Fixed pytest async io deprecation warning.
* Added the `--incident-id` argument (optional) to the **run** command.
* Fixed an issue in **run-unit-tests** and **update-content-graph** where running commands in a docker container was done with insufficient permissions.
* Added the `_time` field to the output compare table of the **modeling-rules test** command.
* Changed the endpoint **download** uses to get system content items.
* Fixed an issue where graph-related tasks failed when files were deleted from the repo.
* Added a **validate** check, and a **format** auto fix for the `fromversion` field in Correlation Rules and XSIAM Dashboards.
* Update the format used for dev-dependencies in pyproject.toml to match modern versions of Poetry.
* Added timestamps to logging messages when running in a CI build.

## 1.15.5
* **Breaking Change**: The default of the **upload** command `--zip` argument is `true`. To upload packs as custom content items use the `--no-zip` argument.
* Removed the `no-implicit-optional` hook from **pre-commit**.
* Removed the `markdownlint` hook from **pre-commit**.
* Fixed an issue in **run-unit-tests** to pass with warnings when no tests are collected.
* Fixed an issue in **run-unit-tests** with the coverage calculation.
* Fixed a notification about log file location appeared more than once.
* Updated the error message when code coverage is below the threshold in **coverage-analyze** to be printed in a more noticeable red color.
* Fixed an issue in **upload** that failed when a comma-separated list of paths is passed to the `--input` argument.
* Running **validate** with the `--graph` flag will now run the graph validations after all other validations.
* improved the generated release note for newly added XSIAM entities when running *update-release-notes* command.
* Fixed an issue where in some cases validation failed when mapping null values.
* Fixed an issue in **upload** command where the `--keep-zip` argument did not clean the working directory.
* Fixed an issue where an extra levelname was added to a logging message.
* Fixed an issue in **upload** where uploading packs to XSIAM failed due to version mismatch.

## 1.15.4
* Fixed an issue where *update-release-notes* and *doc-review* did not handle new content notes as expected.
* Fixed an issue in PEP484 (no-implicit-optional) hook to **pre-commit**.
* Fixed an issue in **upload** with `--input-config-file` where the content items weren't uploaded in the correct pack.
* Added support to disable the default logging colors with the **DEMISTO_SDK_LOG_NO_COLORS** environment variable.

## 1.15.3
* Added the `--init` flag to **download**.
* Added the `--keep-empty-folders` flag to **download**.
* Added `markdown-lint` to **pre-commit**
* Added the PEP484 (no-implicit-optional) hook to **pre-commit**.
* Fixed an issue where the content-graph parsing failed on mappers with undefined mapping.
* Fixed an issue in **validate** where `pack_metadata.json` files were not collected proplely in `--graph` option.
* Fixed an issue where *validate* reputation commands outputs were not checked for new content.
* Added *IN107* and *DB100* error codes to *ALLOWED_IGNORE_ERRORS* list.
* Added a validation that assures feed integrations implement the `integration_reliability` configuration parameter.
* Fixed an issue where the format command did not work as expected on pre-process rules files.
* Fixed an issue where **upload** command failed to upload when the XSOAR version is beta.
* Fixed an issue where **upload** command summary was inaccurate when uploading a `Pack` without the `-z` flag.
* Added pack name and pack version to **upload** command summary.
* Added support for modeling rules with multi datasets in ****modeling-rules test**** command.
* Fixed an issue where **validate** didn't recognize layouts with incident fields missing from `id_set.json` even when `--post-commit` was indicated.

## 1.15.2
* Fixed an issue where **format** added default arguments to reputation commands which already have one.
* Fixed an issue where **validate** fails when adding the *advance* field to the integration required fields.
* Updated the integration Traffic Light Protocol (TLP) color list schema in the **validate** command.
* Fixed an issue where **upload** would not read a repo configuration file properly.
* Fixed an issue where **upload** would not handle the `-x`/`--xsiam` flag properly.
* Fixed an issue where **format** failed to use input from the user, when asking about a `from_version`.
* Added the `-n`/`--assume_no` flag to **format**.

## 1.15.1
* Fixed an issue where **generate-docs** generated fields with double html escaping.
* Fixed an issue where **upload** failed when using the `-z` flag.

## 1.15.0
* **Breaking Change**: the **upload** command now only supports **XSOAR 6.5** or newer (and all XSIAM versions).
* **upload** now uses content models, and calls the `prepare` method of each model before uploading (unless uploading a zipped pack).
* Added a *playbook* modification to **prepare-content**, replacing `getIncident` calls with `getAlerts`, when uploading to XSIAM.
* Added a *playbook* modification to **prepare-content**, replacing `${incident.fieldname}` context accessors with `${alert.fieldname}` when uploading to XSIAM.
* Added a *playbook* modification to **prepare-content**, replacing `incident` to `alert` in task display names, when uploading to XSIAM.
* Added a *layout* modification to **prepare-content**, replacing `Related/Child/Linked Incidents` to `... Alerts` when uploading to XSIAM.
* Added a *script* modification to **prepare-content**, automatically replacing the word `incident` with `alert` when uploading to XSIAM.
* Added a validation that the **validate** command will fail if the `dockerimage` field in scripts/integrations uses any py3-native docker image.
* Updated the `ruff` version used in **pre-commit** to `0.0.269`.
* Fixed an issue in **create-content-graph** which caused missing detection of duplicated content items.
* Fixed an issue where **run-unit-tests** failed on python2 content items.
* Fixed an issue in **validate** where core packs validations were checked against the core packs defined on master branch, rather than on the current branch.
* Fixed an issue in **pre-commit** where `--input` flag was not filtered by the git files.
* Skip reset containers for XSOAR NG and XSIAM(PANW-internal only).
* Fixed an issue where **lint** failed fetching docker image details from a PANW GitLab CI environment. (PANW-internal only).

## 1.14.5
* Added logging in case the container fails to run in **run-unit-tests**.
* Disabled **pre-commit** multiprocessing for `validate` and `format`, as they use a service.
* **pre-commit** now calls `format` with `--assume-yes` and `--no-validate`.
* Fixed an issue where **pre-commit** ran multiple times when checking out build related files.

## 1.14.4
* Added integration configuration for *Cortex REST API* integration.
* Removed `Flake8` from **pre-commit**, as `ruff` covers its basic rules.
* Improved log readability by silencing non-critical `neo4j` (content graph infrastructure) logs.
* Fixed an issue where **run-unit-tests** failed on python2 content items.
* Fixed an issue where **modeling-rules test** did not properly handle query fields that pointed to a string.
* Fixed an issue when trying to fetch remote files when not under the content repo.
* Fixed a validation that the **modeling-rules test** command will fail if no test data file exist.
* Fixed an issue where **format** command failed while updating the `fromversion` entry.
* Added support for mapping uuid to names for Layout files in the **download** command.

## 1.14.3
* Fixed an issue where **run-unit-tests** failed running on items with `test_data`.
* Updated the demisto-py to v3.2.10 which now supports url decoding for the proxy authentication password.
* Fixed an issue where **generate-outputs** did not generate context paths for empty lists or dictionaries in the response.

## 1.14.2
* Added the `--staged-only` flag to **pre-commit**.
* Fixed an issue where **run-unit-tests** failed running on items with `test_data`.
* Fixed an issue where **pre-commit** ran on unchanged files.
* Add the ability to run **secrets** in **pre-commit** by passing a `--secrets` flag.
* Added support to override the log file with the **DEMISTO_SDK_LOG_FILE_PATH** environment variable.

## 1.14.1
* Fixed an issue where **update-release-notes** command failed when running on a pack that contains deprecated integrations without the `commands` section.
* Added toVersion and fromVersion to XSIAM content items schema.
* Fixed an issue where **validate** failed when attempting to map null values in a classifier and layout.
* Added search marketplace functionality to XSIAM client.
* Fixed an issue in **pre-commit** command where `MYPYPATH` was not set properly.
* Updated the integration category list in the **init** command.
* Fixed an issue where in some environments docker errors were not caught.
* Added a validation that the **validate** command will fail on README files if an image does not exist in the specified path.

## 1.14.0
* Added the `DEMISTO_SDK_GRAPH_FORCE_CREATE` environment variable. Use it to force the SDK to recreate the graph, rather than update it.
* Added support for code importing multi-level ApiModules to **lint**.
* Added a validation that the **modeling-rules test** command will fail if no test data file exist.
* Added support for the `<~XPANSE>` marketplace tag in release notes.
* Added support for marketplace tags in the **doc-review** command.
* Added **generate-unit-tests** documentation to the repo README.
* Added the `hiddenpassword` field to the integration schema, allowing **validate** to run on integrations with username-only inputs.
* Improved logs and error handling in the **modeling-rules test** command.
* Improved the warning message displayed for Contribution PRs editing outdated code.
* Improved the clarity of error messages for cases where yml files cannot be parsed as a dictionary.
* Updated the `XSIAMReport` schema.
* Standardized repo-wide logging. All logs are now created in one logger instance.
* **lint** now prevents unit-tests from accessing online resources in runtime.
* Updated the logs shown during lint when running in docker.
* Fixed an issue where **validate** showed errors twice.
* Fixed an issue where **validate** did not fail when xif files had wrong naming.
* Fixed an issue where **doc-review** required dot suffixes in release notes describing new content.
* Fixed an issue where **download** command failed when running on a beta integration.
* Fixed an issue where **update-release-notes** generated release notes for packs in their initial version (1.0.0).
* Fixed an issue with **update-content-graph** where `--use-git` parameter was ignored when using `--imported-path` parameter.
* Fixed an issue where **validate** failed on playbooks with valid inputs, since it did not collect the playbook inputs occurrences properly.

## 1.13.0
* Added the pack version to the code files when calling **unify**. The same value is removed when calling **split**.
* Added a message showing the output path when **prepare-content** is called.
* Contribution PRs that update outdated packs now display a warning message.
* Fixed an issue when kebab-case has a misspelling in one of the sub words, the suggestion might be confusing.
* Improved caching and stability for **lint**.
* Added support for *.xif* files in the **secrets** command.
* Fixed an issue where **validate** would fail when playbook inputs contain Transform Language (DT).
* Added a new **validate** check, making sure a first level header exist in release notes (RN116)
* Fixed an issue where **lint** would not properly handle multiple ApiModules imports.

## 1.12.0
* Added the **pre-commit** command, to improve code quality of XSOAR content.
* Added the **run-unit-tests** command, to run unit tests of given content items inside their respective docker images.
* Added support for filepath arguments in the **validate** and **format** commands.
* Added pre-commit hooks for `validate`, `format`, `run-unit-tests` and `update-docker-image` commands.
* Fixed an issue in the **download** command where layouts were overriden even without the `-f` option.
* Fixed an issue where Demisto-SDK did not detect layout ID when using the **download** command.
* Fixed an issue where the **lint** command ran on `native:dev` supported content when passing the `--docker-image all` flag, instead it will run on `native:candidate`.
* Added support for `native:candidate` as a docker image flag for **lint** command.
* Added a modification for layouts in **prepare-content**, replacing `Related Incidents`, `Linked Incidents` and `Child Incidents` with the suitable `... Alerts` name when uploading to XSIAM.
* Fixed an issue where logs and messages would not show when using the **download** command.
* Fixed an issue where the `server_min_version` field in metadata was an empty value when parsing packs without content items.
* Fixed an issue where running **openapi-codegen** resulted in false-positive error messages.
* Fixed an issue where **generate-python-to-yml** generated input arguments as required even though required=False was specified.
* Fixed an issue where **generate-python-to-yml** generated input arguments a default arguments when default=some_value was provided.
* Fixed a bug where **validate** returned error on playbook inputs with special characters.
* Fixed an issue where **validate** did not properly check `conf.json` when the latter is modified.
* Fixed an issue in the **upload** command, where a prompt was not showing on the console.
* Fixed an issue where running **lint** failed installing dependencies in containers.

## 1.11.0
* **Note: Demisto-SDK will soon stop supporting Python 3.8**
* Fixed an issue where using **download** on non-unicode content, merging them into existing files caused an error.
* Changed an internal setting to allow writing non-ascii content (unicode) using `YAMLHandler` and `JSONHandler`.
* Fixed an issue where an error message in **unify** was unclear for invalid input.
* Fixed an issue where running **validate** failed with **is_valid_integration_file_path_in_folder** on integrations that use API modules.
* Fixed an issue where **validate** failed with **is_valid_integration_file_path_in_folder** on integrations that use the `MSAPIModule`.
* Added **validate** check for the `modules` field in `pack_metadata.json` files.
* Changed **lint** to skip deprecated content, unless when using the `-i` flag.
* Fixed an issue where **update-release-notes** failed when a new *Parsing Rule* was added to a pack.
* Refactored the logging framework. Demisto-SDK logs will now be written to `.demist_sdk_debug.log` under the content path (when detected) or the current directory.
* Added `GR105` validation to **validate** command to check that no duplicate IDs are used.
* Added support for API Modules imported in API modules in the **unify** command.
* Added **validate** check, to make sure every Python file has a corresponding unit test file.

## 1.10.6
* Fixed an issue where running **validate** with the `-g` flag would skip some validations for old-formatted (unified) integration/script files.
* Deprecated integrations and scripts will not run anymore when providing the **--all-packs** to the **lint** command.
* Fixed an issue where a pack `serverMinVersion` would be calculated by the minimal fromVersion of its content items.
* Added the `--docker-image-target` flag to **lint** for testing native supported content with new images.

## 1.10.5
* Fixed an issue where running **run-test-playbook** would not use the `verify` parameter correctly. @ajoga
* Added a newline at the end of README files generated in **generate-docs**.
* Added the value `3` (out of bounds) to the `onChangeRepAlg` and `reputationCalc` fields under the `IncidentType` and `GenericType` schemas. **validate** will allow using it now.
* Fixed an issue where **doc-review** required dot suffixes in release notes describing new content.
* Fixed an issue where **validate** failed on Feed Integrations after adding the new *Collect/Connect* section field.
* Fixed an issue where using **postman-codegen** failed converting strings containing digits to kebab-case.
* Fixed an issue where the ***error-code*** command could not parse List[str] parameter.
* Updated validation *LO107* to support more section types in XSIAM layouts.

## 1.10.4
* Added support for running **lint** in multiple native-docker images.

## 1.10.3
* Fixed an issue where running **format** would fail after running npm install.
* Improved the graph validations in the **validate** command:
  - GR100 will now run on all content items of changed packs.
  - GR101 and GR102 will now catch invalid fromversion/toversion of files **using** the changed items.
  - GR103 errors will raise a warning when using the *-a* flag, but an error if using the *-i* or *g* flags.
* Fixed an issue where test-playbooks timed out.
* Fixed an issue where making a change in a module using an ApiModule would cause lint to run on the ApiModule unnecessarily.
* Fixed an issue where the `marketplace` field was not used when dumping pack zips.
* Fixed a typo in the README content generated with **update-release-notes** for updating integrations.
* Fixed an issue in **validate**, where using the `-gr` and `-i` flags did not run properly.
* Added the `sectionorder` field to integration scheme.
* Fixed an issue where in some occasions running of test-playbooks could receive session timeouts.
* Fixed an issue where **validate** command failed on core pack dependencies validation because of test dependencies.

## 1.10.2
* Added markdown lint formatting for README files in the **format** command.
* Fixed an issue where **lint** failed when using the `-cdam` flag with changed dependant api modules.
* Fixed an issue in the **upload** command, where `json`-based content items were not unified correctly when using the `--zip` argument.
* Added XPANSE core packs validations.

## 1.10.1
* Fixed an issue where **update-content-graph** failed to execute.

## 1.10.0
* **Breaking change**: Removed usage of `pipenv`, `isort` and `autopep8` in the **split** and **download** commands. Removed the `--no-pipenv` and `--no-code-formatting` flags. Please see https://xsoar.pan.dev/docs/tutorials/tut-setup-dev-remote for the recommended environment setup.
* Fixed an issue in **prepare-content** command where large code lines were broken.
* Fixed an issue where git-*renamed_files* were not retrieved properly.
* Fixed an issue where test dependencies were calculated in all level dependencies calculation.
* Added formatting and validation to XSIAM content types.
* Fixed an issue where several XSIAM content types were not validated when passing the `-a` flag.
* Added a UUID to name mapper for **download** it replaces UUIDs with names on all downloaded files.
* Updated the demisto-py to v3.2.6 which now supports basic proxy authentication.
* Improved the message shown when using **upload** and overwriting packs.
* Added support for the **Layout Rule** content type in the id-set and the content graph.
* Updated the default general `fromVersion` value on **format** to `6.8.0`
* Fixed an issue where **lint** sometimes failed when using the `-cdam` flag due to wrong file duplications filtering.
* Added the content graph to **validate**, use with the `--graph` flag.

## 1.9.0
* Fixed an issue where the Slack notifier was using a deprecated argument.
* Added the `--docker-image` argument to the **lint** command, which allows determining the docker image to run lint on. Possible options are: `'native:ga'`, `'native:maintenance'`, `'native:dev'`, `'all'`, a specific docker image (from Docker Hub) or, the default `'from-yml'`.
* Fixed an issue in **prepare-content** command where large code lines were broken.
* Added a logger warning to **get_demisto_version**, the task will now fail with a more informative message.
* Fixed an issue where the **upload** and **prepare-content** commands didn't add `fromServerVersion` and `toServerVersion` to layouts.
* Updated **lint** to use graph instead of id_set when running with `--check-dependent-api-module` flag.
* Added the marketplaces field to all schemas.
* Added the flag `--xsoar-only` to the **doc-review** command which enables reviewing documents that belong to XSOAR-supported Packs.
* Fixed an issue in **update-release-notes** command where an error occurred when executing the same command a second time.
* Fixed an issue where **validate** would not always ignore errors listed under `.pack-ignore`.
* Fixed an issue where running **validate** on a specific pack didn't test all the relevant entities.
* Fixed an issue where fields ending with `_x2` where not replaced in the appropriate Marketplace.

## 1.8.3
* Changed **validate** to allow hiding parameters of type 0, 4, 12 and 14 when replacing with type 9 (credentials) with the same name.
* Fixed an issue where **update-release-notes** fails to update *MicrosoftApiModule* dependent integrations.
* Fixed an issue where the **upload** command failed because `docker_native_image_config.json` file could not be found.
* Added a metadata file to the content graph zip, to be used in the **update-content-graph** command.
* Updated the **validate** and **update-release-notes** commands to unskip the *Triggers Recommendations* content type.


## 1.8.2
* Fixed an issue where demisto-py failed to upload content to XSIAM when `DEMISTO_USERNAME` environment variable is set.
* Fixed an issue where the **prepare-content** command output invalid automation name when used with the --*custom* argument.
* Fixed an issue where modeling rules with arbitrary whitespace characters were not parsed correctly.
* Added support for the **nativeImage** key for an integration/script in the **prepare-content** command.
* Added **validate** checks for integrations declared deprecated (display name, description) but missing the `deprecated` flag.
* Changed the **validate** command to fail on the IN145 error code only when the parameter with type 4 is not hidden.
* Fixed an issue where downloading content layouts with `detailsV2=None` resulted in an error.
* Fixed an issue where **xdrctemplate** was missing 'external' prefix.
* Fixed an issue in **prepare-content** command providing output path.
* Updated the **validate** and **update-release-notes** commands to skip the *Triggers Recommendations* content type.
* Added a new validation to the **validate** command to verify that the release notes headers are in the correct format.
* Changed the **validate** command to fail on the IN140 error code only when the skipped integration has no unit tests.
* Changed **validate** to allow hiding parameters of type 4 (secret) when replacing with type 9 (credentials) with the same name.
* Fixed an issue where the **update-release-notes** command didn't add release-notes properly to some *new* content items.
* Added validation that checks that the `nativeimage` key is not defined in script/integration yml.
* Added to the **format** command the ability to remove `nativeimage` key in case defined in script/integration yml.
* Enhanced the **update-content-graph** command to support `--use-git`, `--imported_path` and `--output-path` arguments.
* Fixed an issue where **doc-review** failed when reviewing command name in some cases.
* Fixed an issue where **download** didn't identify playbooks properly, and downloaded files with UUIDs instead of file/script names.

## 1.8.1
* Fixed an issue where **format** created duplicate configuration parameters.
* Added hidden properties to integration command argument and script argument.
* Added `--override-existing` to **upload** that skips the confirmation prompt for overriding existing content packs. @mattbibbydw
* Fixed an issue where **validate** failed in private repos when attempting to read from a nonexisting `approved_categories.json`.
* Fixed an issue where **validate** used absolute paths when getting remote `pack_metadata.json` files in private repos.
* Fixed an issue in **download**, where names of custom scripts were replaced with UUIDs in IncidentFields and Layouts.

## 1.8.0
* Updated the supported python versions, as `>=3.8,<3.11`, as some of the dependencies are not supported on `3.11` yet.
* Added a **validate** step for **Modeling Rules** testdata files.
* Added the **update-content-graph** command.
* Added the ability to limit the number of CPU cores with `DEMISTO_SDK_MAX_CPU_CORES` envirment variable.
* Added the **prepare-content** command.
* Added support for fromversion/toversion in XSIAM content items (correlation rules, XSIAM dashboards, XSIAM reports and triggers).
* Added a **validate** step checking types of attributes in the schema file of modeling rule.
* Added a **validate** step checking that the dataset name of a modeling rule shows in the xif and schema files.
* Added a **validate** step checking that a correlation rule file does not start with a hyphen.
* Added a **validate** step checking that xsiam content items follow naming conventions.
* Fixed an issue where SDK commands failed on the deprecated `packaging.version.LegacyVersion`, by locking the `packaging` version to `<22`.
* Fixed an issue where **update-release-notes** failed when changing only xif file in **Modeling Rules**.
* Fixed an issue where *is_valid_category* and *is_categories_field_match_standard* failed when running in a private repo.
* Fixed an issue where **validate** didn't fail on the MR103 validation error.
* Fixed the *--release-notes* option, to support the new CHANGELOG format.
* Fixed an issue where **validate** failed when only changing a modeling rules's xif file.
* Fixed an issue where **format** failed on indicator files with a `None` value under the `tabs` key.
* Fixed an issue where **validate** only printed errors for one change of context path, rather than print all.
* Fixed an issue where **download** did not suggest using a username/password when authenticating with XSOAR and using invalid arguments.
* Fixed an issue where **download** failed when listing or downloading content items that are not unicode-encoded.
* Added support for fromversion/toversion in XSIAM content items (correlation rules, XSIAM dashboards, XSIAM reports and triggers).
* Updated the supported python versions, as `>=3.8,<3.11`, as some of the dependencies are not supported on `3.11` yet.
* Added **prepare-content** command which will prepare the pack or content item for the platform.
* Patched an issue where deprecated `packaging.version.LegacyVersion`, locking packaging version to `<22`.

## 1.7.9
* Fixed an issue where an error message in **validate** would not include the suggested fix.
* Added a validation that enforces predefined categories on MP Packs & integration yml files, the validation also ensures that each pack has only one category.
* Fixed an issue where **update-release-notes** did not generate release notes for **XDRC Templates**.
* Fixed an issue where **upload** failed without explaining the reason.
* Improved implementation of the docker_helper module.
* Fixed an issue where **validate** did not check changed pack_metadata.json files when running using git.
* Added support for **xdrctemplate** to content graph.
* Fixed an issue where local copies of the newly-introduced `DemistoClassApiModule.py` were validated.
* Added new release notes templates for the addition and modification of playbooks, layouts and types in the **doc-review** command.
* Fixed an issue where the **doc-review** command failed on descriptions of new content items.
* Added the `Command XXX is deprecated. Use XXX instead.` release notes templates to **doc-review** command.
* Fixed an issue where the **update-release-notes** command didn't add the modeling-rules description for new modeling-rules files.

## 1.7.8
* Added the capability to run the MDX server in a docker container for environments without node.
* Fixed an issue where **generate-docs** with `-c` argument updated sections of the incorrect commands.
* Added IF113 error code to **ALLOWED_IGNORE_ERRORS**.
* Fixed an issue where **validate** failed on playbooks with non-string input values.
* Added the `DEMISTO_SDK_IGNORE_CONTENT_WARNING` environment variable, to allow suppressing warnings when commands are not run under a content repo folder.
* Fixed an issue where **validate** failed to recognize integration tests that were missing from config.json
* Added support for **xpanse** marketplace in **create-id-set** and **create-content-artifacts** commands.
* Fixed an issue where **split** failed on yml files.
* Added support for marketplace-specific tags.
* Fixed an issue where **download** would not run `isort`. @maxgubler
* Fixed an issue where XSIAM Dashboards and Reports images failed the build.
* Added support for **xpanse** marketplace to content graph.

## 1.7.7
* Fixed an issue where paybooks **generate-docs** didn't parse complex input values when no accessor field is given correctly.
* Fixed an issue in the **download** command, where an exception would be raised when downloading system playbooks.
* Fixed an issue where the **upload** failed on playbooks containing a value that starts with `=`.
* Fixed an issue where the **generate-unit-tests** failed to generate assertions, and generate unit tests when command names does not match method name.
* Fixed an issue where the **download** command did not honor the `--no-code-formatting` flag properly. @maxgubler
* Added a new check to **validate**, making sure playbook task values are passed as references.
* Fixed an issue where the **update-release-notes** deleted existing release notes, now appending to it instead.
* Fixed an issue where **validate** printed blank space in case of validation failed and ignored.
* Renamed 'Agent Config' to 'XDRC Templates'.
* Fixed an issue where the **zip-packs** command did not work with the CommonServerUserPython and CommonServerUserPowerShell package.

## 1.7.6

* Fixed parsing of initialization arguments of client classes in the **generate-unit-tests** command.
* Added support for AgentConfig content item in the **upload**, **create-id-set**, **find-dependecies**, **unify** and **create-content-artifacts** commands.
* Added support for XSIAM Report preview image.

## 1.7.5

* Fixed an issue where the **upload** command did not work with the CommonServerUserPython package.
* Fixed an issue in the **download** command, where some playbooks were downloaded as test playbooks.
* Added playbook modification capabilities in **TestSuite**.
* Added a new command **create-content-graph**.
* Fixed an issue in the **upload** command, where the temporary zip would not clean up properly.
* Improved content items parsing in the **create-content-graph** command.
* Added an error when the docker daemon is unavailable when running **lint**.
* Removed the validation of a subtype change for scripts in the **validate** command.
* Fixed an issue where names of XSIAM content items were not normalized properly.
* Fixed an issue where the **download** command was downloading playbooks with **script** (id) and not **scriptName**.
* Fixed an issue where script yml files were not properly identified by `find_type`.
* Removed nightly integrations filtering when deciding if a test should run.
* Added support for XSIAM Dashboard preview image.
* Added the `--no-code-formatting` flag to the **download** command, allowing to skip autopep8 and isort.
* Fixed an issue in the **update-release-notes** command, where generating release notes for modeling rules schema file caused exception.

## 1.7.4

* Fixed an issue where the **doc-review** command showed irrelevant messages.
* Fixed an issue in **validate**, where backward-compatibility failures prevented other validations from running.
* Fixed an issue in **validate**, where content-like files under infrastructure paths were not ignored.
* Fixed an issue in the AMI mapping, where server versions were missing.
* Change the way the normalize name is set for external files.
* Added dump function to XSIAM pack objects to dulicate the files.
* Fixed an issue where the `contribution_converter` did not support changes made to ApiModules.
* Added name normalization according to new convention to XSIAM content items
* Added playbook modification capabilities in **TestSuite**.
* Fixed an issue in create-content-artifacts where it will not get a normalize name for the item and it will try to duplicate the same file.

## 1.7.3

* Fixed an issue in the **format** command where fail when executed from environment without mdx server available.
* Added `Added a`, `Added an` to the list of allowed changelog prefixes.
* Added support for Indicator Types/Reputations in the **upload** command.
* Fixed an issue when running from a subdirectory of a content repo failed.
* Changing the way we are using XSIAM servers api-keys in **test-content** .
* Added a success message to **postman-codegen**.

## 1.7.2

* Fixed an issue in the **validate** command where incident fields were not found in mappers even when they exist
* Added an ability to provide list of marketplace names as a param attribute to **validate** and **upload**
* Added the file type to the error message when it is not supported.
* Fixed an issue where `contribution_converter` incorrectly mapped _Indicator Field_ objects to the _incidentfield_ directory in contribution zip files.
* Fixed a bug where **validate** returned error on empty inputs not used in playbooks.
* Added the `DEMISTO_SDK_CONTENT_PATH` environment variable, implicitly used in various commands.
* Added link to documentation for error messages regarding use cases and tags.

## 1.7.1

* Fixed an issue where *indicatorTypes* and *betaIntegrations* were not found in the id_set.
* Updated the default general `fromVersion` value on **format** to `6.5.0`
* Fixed an issue where the **validate** command did not fail when the integration yml file name was not the same as the folder containing it.
* Added an option to have **generate-docs** take a Playbooks folder path as input, and generate docs for all playbooks in it.
* Fixed an issue where the suggestion in case of `IF113` included uppercase letters for the `cliName` parameter.
* Added new validation to the **validate** command to fail and list all the file paths of files that are using a deprecated integration command / script / playbook.
* **validate** will no longer fail on playbooks calling subplaybooks that have a higher `fromVersion` value, if  calling the subplaybook has `skipifunavailable=True`.
* Fixed an issue where relative paths were not accessed correctly.
* Running any `demisto-sdk` command in a folder with a `.env` file will load it, temporarily overriding existing environment variables.
* Fixed an issue where **validate** did not properly detect deleted files.
* Added new validations to the **validate** command to verify that the schema file exists for a modeling rule and that the schema and rules keys are empty in the yml file.
* Fixed an issue where *find_type* didn't recognize exported incident types.
* Added a new validation to **validate**, making sure all inputs of a playbook are used.
* Added a new validation to **validate**, making sure all inputs used in a playbook declared in the input section.
* The **format** command will now replace the *fromServerVersion* field with *fromVersion*.

## 1.7.0

* Allowed JSON Handlers to accept kwargs, for custoimzing behavior.
* Fixed an issue where an incorrect error was shown when the `id` of a content item differed from its `name` attribute.
* Fixed an issue where the `preserve_quotes` in ruamel_handler received an incorrect value @icholy
* Fixed an issue where ignoring RM110 error code wasn't working and added a validation to **ALLOWED_IGNORE_ERRORS** to validate that all error codes are inserted in the right format.
* Fixed an issue where the contribution credit text was not added correctly to the pack README.
* Changed the contribution file implementation from markdown to a list of contributor names. The **create-content-artifact** will use this list to prepare the needed credit message.
* Added a new validation to the `XSOAR-linter` in the **lint** command for verifying that demisto.log is not used in the code.
* The **generate-docs** command will now auto-generate the Incident Mirroring section when implemented in an integration.
* Added support to automatically generate release notes for deprecated items in the **update-release-notes** command.
* Fixed an issue causing any command to crash when unable to detect local repository properties.
* Fixed an issue where running in a private gitlab repo caused a warning message to be shown multiple times.
* Added a new validation to the **validate** command to verify that markdown and python files do not contain words related to copyright section.
* Fixed an issue where **lint** crashed when provided an input file path (expecting a directory).

## 1.6.9

* Added a new validation that checks whether a pack should be deprecated.
* Added a new ability to the **format** command to deprecate a pack.
* Fixed an issue where the **validate** command sometimes returned a false negative in cases where there are several sub-playbooks with the same ID.
* Added a new validation to the **validate** command to verify that the docker in use is not deprecated.
* Added support for multiple ApiModules in the **unify** command
* Added a check to **validate** command, preventing use of relative urls in README files.
* Added environment variable **DEMISTO_SDK_MARKETPLACE** expected to affect *MarketplaceTagParser* *marketplace* value. The value will be automatically set when passing *marketplace* arg to the commands **unify**, **zip-packs**, **create-content-artifacts** and **upload**.
* Added slack notifier for build failures on the master branch.
* Added support for modeling and parsing rules in the **split** command.
* Added support for README files in **format** command.
* Added a **validate** check, making sure classifier id and name values match. Updated the classifier **format** to update the id accordingly.
* The **generate-docs** command will now auto-generate the playbook image link by default.
* Added the `--custom-image-link` argument to override.
* Added a new flag to **generate-docs** command, allowing to add a custom image link to a playbook README.
* Added a new validation to the **validate** command to verify that the package directory name is the same as the files contained in the that package.
* Added support in the **unify** command to unify a schema into its Modeling Rule.

## 1.6.8

* Fixed an issue where **validate** did not fail on invalid playbook entities' versions (i.e. subplaybooks or scripts with higher fromversion than their parent playbook).
* Added support for running lint via a remote docker ssh connection. Use `DOCKER_HOST` env variable to specify a remote docker connection, such as: `DOCKER_HOST=ssh://myuser@myhost.com`.
* Fixed an issue where the pack cache in *get_marketplaces* caused the function to return invalid values.
* Fixed an issue where running format on a pack with XSIAM entities would fail.
* Added the new `display_name` field to relevant entities in the **create-id-set** command.
* Added a new validation to the **validate** command to verify the existence of "Reliability" parameter if the integration have reputation command.
* Fixed a bug where terminating the **lint** command failed (`ctrl + c`).
* Removed the validation of a subtype change in integrations and scripts from **validate**.
* Fixed an issue where **download** did not behave as expected when prompting for a version update. Reported by @K-Yo
* Added support for adoption release notes.
* Fixed an issue where **merge-id-sets** failed when a key was missing in one id-set.json.
* Fixed a bug where some mypy messages were not parsed properly in **lint**.
* Added a validation to the **validate** command, failing when '`fromversion`' or '`toversion`' in a content entity are incorrect format.
* Added a validation to the **validate** command, checking if `fromversion` <= `toversion`.
* Fixed an issue where coverage reports used the wrong logging level, marking debug logs as errors.
* Added a new validation to the **validate** command, to check when the discouraged `http` prefixes are used when setting defaultvalue, rather than `https`.
* Added a check to the **lint** command for finding hard-coded usage of the http protocol.
* Locked the dependency on Docker.
* Removed a traceback line from the **init** command templates: BaseIntegration, BaseScript.
* Updated the token in **_add_pr_comment** method from the content-bot token to the xsoar-bot token.

## 1.6.7

* Added the `types-markdown` dependency, adding markdown capabilities to existing linters using the [Markdown](https://pypi.org/project/Markdown/) package.
* Added support in the **format** command to remove nonexistent incident/indicator fields from *layouts/mappers*
* Added the `Note: XXX` and `XXX now generally available.` release notes templates to **doc-review** command.
* Updated the logs shown during the docker build step.
* Removed a false warning about configuring the `GITLAB_TOKEN` environment variable when it's not needed.
* Removed duplicate identifiers for XSIAM integrations.
* Updated the *tags* and *use cases* in pack metadata validation to use the local files only.
* Fixed the error message in checkbox validation where the defaultvalue is wrong and added the name of the variable that should be fixed.
* Added types to `find_type_by_path` under tools.py.
* Fixed an issue where YAML files contained incorrect value type for `tests` key when running `format --deprecate`.
* Added a deprecation message to the `tests:` section of yaml files when running `format --deprecate`.
* Added use case for **validate** on *wizard* objects - set_playbook is mapped to all integrations.
* Added the 'integration-get-indicators' commands to be ignored by the **verify_yml_commands_match_readme** validation, the validation will no longer fail if these commands are not in the readme file.
* Added a new validation to the **validate** command to verify that if the phrase "breaking changes" is present in a pack release notes, a JSON file with the same name exists and contains the relevant breaking changes information.
* Improved logs when running test playbooks (in a build).
* Fixed an issue in **upload** did not include list-type content items. @nicolas-rdgs
* Reverted release notes to old format.

## 1.6.6

* Added debug print when excluding item from ID set due to missing dependency.
* Added a validation to the **validate** command, failing when non-ignorable errors are present in .pack-ignore.
* Fixed an issue where `mdx server` did not close when stopped in mid run.
* Fixed an issue where `-vvv` flag did not print logs on debug level.
* enhanced ***validate*** command to list all command names affected by a backward compatibility break, instead of only one.
* Added support for Wizard content item in the **format**, **validate**, **upload**, **create-id-set**, **find-dependecies** and **create-content-artifacts** commands.
* Added a new flag to the **validate** command, allowing to run specific validations.
* Added support in **unify** and **create-content-artifacts** for displaying different documentations (detailed description + readme) for content items, depending on the marketplace version.
* Fixed an issue in **upload** where list items were not uploaded.
* Added a new validation to **validate** command to verify that *cliName* and *id* keys of the incident field or the indicator field are matches.
* Added the flag '-x', '--xsiam' to **upload** command to upload XSIAM entities to XSIAM server.
* Fixed the integration field *isFetchEvents* to be in lowercase.
* Fixed an issue where **validate -i** run after **format -i** on an existing file in the repo instead of **validate -g**.
* Added the following commands: 'update-remote-data', 'get-modified-remote-data', 'update-remote-system' to be ignored by the **verify_yml_commands_match_readme** validation, the validation will no longer fail if these commands are not in the readme file.
* Updated the release note template to include a uniform format for all items.
* Added HelloWorldSlim template option for *--template* flag in **demisto-sdk init** command.
* Fixed an issue where the HelloWorldSlim template in **demisto-sdk init** command had an integration id that was conflicting with HelloWorld integration id.
* Updated the SDK to use demisto-py 3.1.6, allowing use of a proxy with an environment variable.
* Set the default logger level to `warning`, to avoid unwanted debug logs.
* The **format** command now validates that default value of checkbox parameters is a string 'true' or 'false'.
* Fixed an issue where `FileType.PLAYBOOK` would show instead of `Playbook` in readme error messages.
* Added a new validation to **validate** proper defaultvalue for checkbox fields.

## 1.6.5

* Fixed an issue in the **format** command where the `id` field was overwritten for existing JSON files.
* Fixed an issue where the **doc-review** command was successful even when the release-note is malformed.
* Added timestamps to the `demisto-sdk` logger.
* Added time measurements to **lint**.
* Added the flag '-d', '--dependency' to **find-dependencies** command to get the content items that cause the dependencies between two packs.
* Fixed an issue where **update-release-notes** used the *trigger_id* field instead of the *trigger_name* field.
* Fixed an issue where **doc-review** failed to recognize script names, in scripts using the old file structure.
* Fixed an issue where concurrent processes created by **lint** caused deadlocks when opening files.
* Fixed an issue in the **format** command where `_dev` or `_copy` suffixes weren't removed from the subscript names in playbooks and layouts.
* Fixed an issue where **validate** failed on nonexistent `README.md` files.
* Added support of XSIAM content items to the **validate** command.
* Report **lint** summary results and failed packages after reporting time measurements.

## 1.6.4

* Added the new **generate-yml-from-python** command.
* Added a code *type* indication for integration and script objects in the *ID Set*.
* Added the [Vulture](https://github.com/jendrikseipp/vulture) linter to the pre-commit hook.
* The `demisto-sdk` pack will now be distributed via PyPi with a **wheel** file.
* Fixed a bug where any edited json file that contained a forward slash (`/`) escaped.
* Added a new validation to **validate** command to verify that the metadata *currentVersion* is
the same as the last release note version.
* The **validate** command now checks if there're none-deprecated integration commands that are missing from the readme file.
* Fixed an issue where *dockerimage* changes in Scripts weren't recognized by the **update-release-notes** command.
* Fixed an issue where **update-xsoar-config-file** did not properly insert the marketplace packs list to the file.
* Added the pack name to the known words by default when running the **doc-review** command.
* Added support for new XSIAM entities in **create-id-set** command.
* Added support for new XSIAM entities in **create-content-artifacts** command.
* Added support for Parsing/Modeling Rule content item in the **unify** command.
* Added the integration name, the commands name and the script name to the known words by default when running the **doc-review** command.
* Added an argument '-c' '--custom' to the **unify** command, if True will append to the unified yml name/display/id the custom label provided
* Added support for sub words suggestion in kebab-case sentences when running the **doc-review** command.
* Added support for new XSIAM entities in **update-release-notes** command.
* Enhanced the message of alternative suggestion words shown when running **doc-review** command.
* Fixed an incorrect error message, in case `node` is not installed on the machine.
* Fixed an issue in the **lint** command where the *check-dependent-api-modules* argument was set to true by default.
* Added a new command **generate-unit-tests**.
* Added a new validation to **validate** all SIEM integration have the same suffix.
* Fixed the destination path of the unified parsing/modeling rules in **create-content-artifacts** command.
* Fixed an issue in the **validate** command, where we validated wrongfully the existence of readme file for the *ApiModules* pack.
* Fixed an issue in the **validate** command, where an error message that was displayed for scripts validation was incorrect.
* Fixed an issue in the **validate** and **format** commands where *None* arguments in integration commands caused the commands to fail unexpectedly.
* Added support for running tests on XSIAM machines in the **test-content** command.
* Fixed an issue where the **validate** command did not work properly when deleting non-content items.
* Added the flag '-d', '--dependency' to **find-dependencies** command to get the content items that cause the dependencies between two packs.

## 1.6.3

* **Breaking change**: Fixed a typo in the **validate** `--quiet-bc-validation` flag (was `--quite-bc-validation`). @upstart-swiss
* Dropped support for python 3.7: Demisto-SDK is now supported on Python 3.8 or newer.
* Added an argument to YAMLHandler, allowing to set a maximal width for YAML files. This fixes an issue where a wrong default was used.
* Added the detach mechanism to the **upload** command, If you set the --input-config-file flag, any files in the repo's SystemPacks folder will be detached.
* Added the reattach mechanism to the **upload** command, If you set the --input-config-file flag, any detached item in your XSOAR instance that isn't currently in the repo's SystemPacks folder will be re-attached.
* Fixed an issue in the **validate** command that did not work properly when using the *-g* flag.
* Enhanced the dependency message shown when running **lint**.
* Fixed an issue where **update-release-notes** didn't update the currentVersion in pack_metadata.
* Improved the logging in **test-content** for helping catch typos in external playbook configuration.

## 1.6.2

* Added dependency validation support for core marketplacev2 packs.
* Fixed an issue in **update-release-notes** where suggestion fix failed in validation.
* Fixed a bug where `.env` files didn't load. @nicolas-rdgs
* Fixed a bug where **validate** command failed when the *categories* field in the pack metadata was empty for non-integration packs.
* Added *system* and *item-type* arguments to the **download** command, used when downloading system items.
* Added a validation to **validate**, checking that each script, integration and playbook have a README file. This validation only runs when the command is called with either the `-i` or the `-g` flag.
* Fixed a regression issue with **doc-review**, where the `-g` flag did not work.
* Improved the detection of errors in **doc-review** command.
* The **validate** command now checks if a readme file is empty, only for packs that contain playbooks or were written by a partner.
* The **validate** command now makes sure common contextPath values (e.g. `DBotScore.Score`) have a non-empty description, and **format** populates them automatically.
* Fixed an issue where the **generate-outputs** command did not work properly when examples were provided.
* Fixed an issue in the **generate-outputs** command, where the outputs were not written to the specified output path.
* The **generate-outputs** command can now generate outputs from multiple calls to the same command (useful when different args provide different outputs).
* The **generate-outputs** command can now update a yaml file with new outputs, without deleting or overwriting existing ones.
* Fixed a bug where **doc-review** command failed on existing templates.
* Fixed a bug where **validate** command failed when the word demisto is in the repo README file.
* Added support for adding test-playbooks to the zip file result in *create-content-artifacts* command for marketplacev2.
* Fixed an issue in **find-dependencies** where using the argument *-o* without the argument *--all-packs-dependencies* did not print a proper warning.
* Added a **validate** check to prevent deletion of files whose deletion is not supported by the XSOAR marketplace.
* Removed the support in the *maintenance* option of the *-u* flag in the **update-release-notes** command.
* Added validation for forbidden words and phrases in the **doc-review** command.
* Added a retries mechanism to the **test-content** command to stabilize the build process.
* Added support for all `git` platforms to get remote files.
* Refactored the **format** command's effect on the *fromversion* field:
  * Fixed a bug where the *fromversion* field was removed when modifying a content item.
  * Updated the general default *fromversion* and the default *fromversion* of newly-introduced content items (e.g. `Lists`, `Jobs`).
  * Added an interactive mode functionality for all content types, to ask the user whether to set a default *fromversion*, if could not automatically determine its value. Use `-y` to assume 'yes' as an answer to all prompts and run non-interactively.

## 1.6.1

* Added the '--use-packs-known-words' argument to the **doc-review** command
* Added YAML_Loader to handle yaml files in a standard way across modules, replacing PYYAML.
* Fixed an issue when filtering items using the ID set in the **create-content-artifacts** command.
* Fixed an issue in the **generate-docs** command where tables were generated with an empty description column.
* Fixed an issue in the **split** command where splitting failed when using relative input/output paths.
* Added warning when inferred files are missing.
* Added to **validate** a validation for integration image dimensions, which should be 120x50px.
* Improved an error in the **validate** command to better differentiate between the case where a required fetch parameter is malformed or missing.

## 1.6.0

* Fixed an issue in the **create-id-set** command where similar items from different marketplaces were reported as duplicated.
* Fixed typo in demisto-sdk init
* Fixed an issue where the **lint** command did not handle all container exit codes.
* Add to **validate** a validation for pack name to make sure it is unchanged.
* Added a validation to the **validate** command that verifies that the version in the pack_metdata file is written in the correct format.
* Fixed an issue in the **format** command where missing *fromVersion* field in indicator fields caused an error.

## 1.5.9

* Added option to specify `External Playbook Configuration` to change inputs of Playbooks triggered as part of **test-content**
* Improved performance of the **lint** command.
* Improved performance of the **validate** command when checking README images.
* ***create-id-set*** command - the default value of the **marketplace** argument was changed from ‘xsoar’ to all packs existing in the content repository. When using the command, make sure to pass the relevant marketplace to use.

## 1.5.8

* Fixed an issue where the command **doc-review** along with the argument `--release-notes` failed on yml/json files with invalid schema.
* Fixed an issue where the **lint** command failed on packs using python 3.10

## 1.5.7

* Fixed an issue where reading remote yaml files failed.
* Fixed an issue in **validate** failed with no error message for lists (when no fromVersion field was found).
* Fixed an issue when running **validate** or **format** in a gitlab repository, and failing to determine its project id.
* Added an enhancement to **split**, handling an empty output argument.
* Added the ability to add classifiers and mappers to conf.json.
* Added the Alias field to the incident field schema.

## 1.5.6

* Added 'deprecated' release notes template.
* Fixed an issue where **run-test-playbook** command failed to get the task entries when the test playbook finished with errors.
* Fixed an issue in **validate** command when running with `no-conf-json` argument to ignore the `conf.json` file.
* Added error type text (`ERROR` or `WARNING`) to **validate** error prints.
* Fixed an issue where the **format** command on test playbook did not format the ID to be equal to the name of the test playbook.
* Enhanced the **update-release-notes** command to automatically commit release notes config file upon creation.
* The **validate** command will validate that an indicator field of type html has fromVersion of 6.1.0 and above.
* The **format** command will now add fromVersion 6.1.0 to indicator field of type html.
* Added support for beta integrations in the **format** command.
* Fixed an issue where the **postman-codegen** command failed when called with the `--config-out` flag.
* Removed the integration documentation from the detailed description while performing **split** command to the unified yml file.
* Removed the line which indicates the version of the product from the README.md file for new contributions.

## 1.5.5

* Fixed an issue in the **update-release-notes** command, which did not work when changes were made in multiple packs.
* Changed the **validate** command to fail on missing test-playbooks only if no unittests are found.
* Fixed `to_kebab_case`, it will now deal with strings that have hyphens, commas or periods in them, changing them to be hyphens in the new string.
* Fixed an issue in the **create-id-set** command, where the `source` value included the git token if it was specified in the remote url.
* Fixed an issue in the **merge-id-set** command, where merging fails because of duplicates but the packs are in the XSOAR repo but in different version control.
* Fixed missing `Lists` Content Item as valid `IDSetType`
* Added enhancement for **generate-docs**. It is possible to provide both file or a comma seperated list as `examples`. Also, it's possible to provide more than one example for a script or a command.
* Added feature in **format** to sync YML and JSON files to the `master` file structure.
* Added option to specify `Incident Type`, `Incoming Mapper` and `Classifier` when configuring instance in **test-content**
* added a new command **run-test-playbook** to run a test playbook in a given XSOAR instance.
* Fixed an issue in **format** when running on a modified YML, that the `id` value is not changed to its old `id` value.
* Enhancement for **split** command, replace `ApiModule` code block to `import` when splitting a YML.
* Fixed an issue where indicator types were missing from the pack's content, when uploading using **zip-packs**.
* The request data body format generated in the **postman-codegen** will use the python argument's name and not the raw data argument's name.
* Added the flag '--filter-by-id-set' to **create-content-artifacts** to create artifacts only for items in the given id_set.json.

## 1.5.4

* Fixed an issue with the **format** command when contributing via the UI
* The **format** command will now not remove the `defaultRows` key from incident, indicator and generic fields with `type: grid`.
* Fixed an issue with the **validate** command when a layoutscontainer did not have the `fromversion` field set.
* added a new command **update-xsoar-config-file** to handle your XSOAR Configuration File.
* Added `skipVerify` argument in **upload** command to skip pack signature verification.
* Fixed an issue when the **run** command  failed running when there’s more than one playground, by explicitly using the current user’s playground.
* Added support for Job content item in the **format**, **validate**, **upload**, **create-id-set**, **find-dependecies** and **create-content-artifacts** commands.
* Added a **source** field to the **id_set** entitles.
* Two entitles will not consider as duplicates if they share the same pack and the same source.
* Fixed a bug when duplicates were found in **find_dependencies**.
* Added function **get_current_repo** to `tools`.
* The **postman-codegen** will not have duplicates argument name. It will rename them to the minimum distinguished shared path for each of them.

## 1.5.3

* The **format** command will now set `unsearchable: True` for incident, indicator and generic fields.
* Fixed an issue where the **update-release-notes** command crashes with `--help` flag.
* Added validation to the **validate** command that verifies the `unsearchable` key in incident, indicator and generic fields is set to true.
* Removed a validation that DBotRole should be set for automation that requires elevated permissions to the `XSOAR-linter` in the **lint** command.
* Fixed an issue in **Validate** command where playbooks conditional tasks were mishandeled.
* Added a validation to prevent contributors from using the `fromlicense` key as a configuration parameter in an integration's YML
* Added a validation to ensure that the type for **API token** (and similar) parameters are configured correctly as a `credential` type in the integration configuration YML.
* Added an assertion that checks for duplicated requests' names when generating an integration from a postman collection.
* Added support for [.env files](https://pypi.org/project/python-dotenv/). You can now add a `.env` file to your repository with the logging information instead of setting a global environment variables.
* When running **lint** command with --keep-container flag, the docker images are committed.
* The **validate** command will not return missing test playbook error when given a script with dynamic-section tag.

## 1.5.2

* Added a validation to **update-release-notes** command to ensure that the `--version` flag argument is in the right format.
* added a new command **coverage-analyze** to generate and print coverage reports.
* Fixed an issue in **validate** in repositories which are not in GitHub or GitLab
* Added a validation that verifies that readme image absolute links do not contain the working branch name.
* Added support for List content item in the **format**, **validate**, **download**, **upload**, **create-id-set**, **find-dependecies** and **create-content-artifacts** commands.
* Added a validation to ensure reputation command's default argument is set as an array input.
* Added the `--fail-duplicates` flag for the **merge-id-set** command which will fail the command if duplicates are found.
* Added the `--fail-duplicates` flag for the **create-id-set** command which will fail the command if duplicates are found.

## 1.5.1

* Fixed an issue where **validate** command failed to recognized test playbooks for beta integrations as valid tests.
* Fixed an issue were the **validate** command was falsely recognizing image paths in readme files.
* Fixed an issue where the **upload** command error message upon upload failure pointed to wrong file rather than to the pack metadata.
* Added a validation that verifies that each script which appears in incident fields, layouts or layout containers exists in the id_set.json.
* Fixed an issue where the **postman code-gen** command generated double dots for context outputs when it was not needed.
* Fixed an issue where there **validate** command on release notes file crashed when author image was added or modified.
* Added input handling when running **find-dependencies**, replacing string manipulations.
* Fixed an issue where the **validate** command did not handle multiple playbooks with the same name in the id_set.
* Added support for GitLab repositories in **validate**

## 1.5.0

* Fixed an issue where **upload** command failed to upload packs not under content structure.
* Added support for **init** command to run from non-content repo.
* The **split-yml** has been renamed to **split** and now supports splitting Dashboards from unified Generic Modules.
* Fixed an issue where the skipped tests validation ran on the `ApiModules` pack in the **validate** command.
* The **init** command will now create the `Generic Object` entities directories.
* Fixed an issue where the **format** command failed to recognize changed files from git.
* Fixed an issue where the **json-to-outputs** command failed checking whether `0001-01-01T00:00:00` is of type `Date`
* Added to the **generate context** command to generate context paths for integrations from an example file.
* Fixed an issue where **validate** failed on release notes configuration files.
* Fixed an issue where the **validate** command failed on pack input if git detected changed files outside of `Packs` directory.
* Fixed an issue where **validate** command failed to recognize files inside validated pack when validation release notes, resulting in a false error message for missing entity in release note.
* Fixed an issue where the **download** command failed when downloading an invalid YML, instead of skipping it.

## 1.4.9

* Added validation that the support URL in partner contribution pack metadata does not lead to a GitHub repo.
* Enhanced ***generate-docs*** with default `additionalinformation` (description) for common parameters.
* Added to **validate** command a validation that a content item's id and name will not end with spaces.
* The **format** command will now remove trailing whitespaces from content items' id and name fields.
* Fixed an issue where **update-release-notes** could fail on files outside the user given pack.
* Fixed an issue where the **generate-test-playbook** command would not place the playbook in the proper folder.
* Added to **validate** command a validation that packs with `Iron Bank` uses the latest docker from Iron Bank.
* Added to **update-release-notes** command support for `Generic Object` entities.
* Fixed an issue where playbook `fromversion` mismatch validation failed even if `skipunavailable` was set to true.
* Added to the **create artifacts** command support for release notes configuration file.
* Added validation to **validate** for release notes config file.
* Added **isoversize** and **isautoswitchedtoquietmode** fields to the playbook schema.
* Added to the **update-release-notes** command `-bc` flag to generate template for breaking changes version.
* Fixed an issue where **validate** did not search description files correctly, leading to a wrong warning message.

## 1.4.8

* Fixed an issue where yml files with `!reference` failed to load properly.
* Fixed an issue when `View Integration Documentation` button was added twice during the download and re-upload.
* Fixed an issue when `(Partner Contribution)` was added twice to the display name during the download and re-upload.
* Added the following enhancements in the **generate-test-playbook** command:
  * Added the *--commands* argument to generate tasks for specific commands.
  * Added the *--examples* argument to get the command examples file path and generate tasks from the commands and arguments specified there.
  * Added the *--upload* flag to specify whether to upload the test playbook after the generation.
  * Fixed the output condition generation for outputs of type `Boolean`.

## 1.4.7

* Fixed an issue where an empty list for a command context didn't produce an indication other than an empty table.
* Fixed an issue where the **format** command has incorrectly recognized on which files to run when running using git.
* Fixed an issue where author image validations were not checked properly.
* Fixed an issue where new old-formatted scripts and integrations were not validated.
* Fixed an issue where the wording in the from version validation error for subplaybooks was incorrect.
* Fixed an issue where the **update-release-notes** command used the old docker image version instead of the new when detecting a docker change.
* Fixed an issue where the **generate-test-playbook** command used an incorrect argument name as default
* Fixed an issue where the **json-to-outputs** command used an incorrect argument name as default when using `-d`.
* Fixed an issue where validations failed while trying to validate non content files.
* Fixed an issue where README validations did not work post VS Code formatting.
* Fixed an issue where the description validations were inconsistent when running through an integration file or a description file.

## 1.4.6

* Fixed an issue where **validate** suggests, with no reason, running **format** on missing mandatory keys in yml file.
* Skipped existence of TestPlaybook check on community and contribution integrations.
* Fixed an issue where pre-commit didn't run on the demisto_sdk/commands folder.
* The **init** command will now change the script template name in the code to the given script name.
* Expanded the validations performed on beta integrations.
* Added support for PreProcessRules in the **format**, **validate**, **download**, and **create-content-artifacts** commands.
* Improved the error messages in **generate-docs**, if an example was not provided.
* Added to **validate** command a validation that a content entity or a pack name does not contain the words "partner" and "community".
* Fixed an issue where **update-release-notes** ignores *--text* flag while using *-f*
* Fixed the outputs validations in **validate** so enrichment commands will not be checked to have DBotScore outputs.
* Added a new validation to require the dockerimage key to exist in an integration and script yml files.
* Enhanced the **generate-test-playbook** command to use only integration tested on commands, rather than (possibly) other integrations implementing them.
* Expanded unify command to support GenericModules - Unifies a GenericModule object with its Dashboards.
* Added validators for generic objects:
  * Generic Field validator - verify that the 'fromVersion' field is above 6.5.0, 'group' field equals 4 and 'id' field starts with the prefix 'generic_'.
  * Generic Type validator - verify that the 'fromVersion' field is above 6.5.0
  * Generic Module validator - verify that the 'fromVersion' field is above 6.5.0
  * Generic Definition validator - verify that the 'fromVersion' field is above 6.5.0
* Expanded Format command to support Generic Objects - Fixes generic objects according to their validations.
* Fixed an issue where the **update-release-notes** command did not handle ApiModules properly.
* Added option to enter a dictionary or json of format `[{field_name:description}]` in the **json-to-outputs** command,
  with the `-d` flag.
* Improved the outputs for the **format** command.
* Fixed an issue where the validations performed after the **format** command were inconsistent with **validate**.
* Added to the **validate** command a validation for the author image.
* Updated the **create-content-artifacts** command to support generic modules, definitions, fields and types.
* Added an option to ignore errors for file paths and not only file name in .pack-ignore file.

## 1.4.5

* Enhanced the **postman-codegen** command to name all generated arguments with lower case.
* Fixed an issue where the **find-dependencies** command miscalculated the dependencies for playbooks that use generic commands.
* Fixed an issue where the **validate** command failed in external repositories in case the DEMISTO_SDK_GITHUB_TOKEN was not set.
* Fixed an issue where **openapi-codegen** corrupted the swagger file by overwriting configuration to swagger file.
* Updated the **upload** command to support uploading zipped packs to the marketplace.
* Added to the **postman-codegen** command support of path variables.
* Fixed an issue where **openapi-codegen** entered into an infinite loop on circular references in the swagger file.
* The **format** command will now set `fromVersion: 6.2.0` for widgets with 'metrics' data type.
* Updated the **find-dependencies** command to support generic modules, definitions, fields and types.
* Fixed an issue where **openapi-codegen** tried to extract reference example outputs, leading to an exception.
* Added an option to ignore secrets automatically when using the **init** command to create a pack.
* Added a tool that gives the ability to temporarily suppress console output.

## 1.4.4

* When formatting incident types with Auto-Extract rules and without mode field, the **format** command will now add the user selected mode.
* Added new validation that DBotRole is set for scripts that requires elevated permissions to the `XSOAR-linter` in the **lint** command.
* Added url escaping to markdown human readable section in generate docs to avoid autolinking.
* Added a validation that mapper's id and name are matching. Updated the format of mapper to include update_id too.
* Added a validation to ensure that image paths in the README files are valid.
* Fixed **find_type** function to correctly find test files, such as, test script and test playbook.
* Added scheme validations for the new Generic Object Types, Fields, and Modules.
* Renamed the flag *--input-old-version* to *--old-version* in the **generate-docs** command.
* Refactored the **update-release-notes** command:
  * Replaced the *--all* flag with *--use-git* or *-g*.
  * Added the *--force* flag to update the pack release notes without changes in the pack.
  * The **update-release-notes** command will now update all dependent integrations on ApiModule change, even if not specified.
  * If more than one pack has changed, the full list of updated packs will be printed at the end of **update-release-notes** command execution.
  * Fixed an issue where the **update-release-notes** command did not add docker image release notes entry for release notes file if a script was changed.
  * Fixed an issue where the **update-release-notes** command did not detect changed files that had the same name.
  * Fixed an issue in the **update-release-notes** command where the version support of JSON files was mishandled.
* Fixed an issue where **format** did not skip files in test and documentation directories.
* Updated the **create-id-set** command to support generic modules, definitions, fields and types.
* Changed the **convert** command to generate old layout fromversion to 5.0.0 instead of 4.1.0
* Enhanced the command **postman-codegen** with type hints for templates.

## 1.4.3

* Fixed an issue where **json-to-outputs** command returned an incorrect output when json is a list.
* Fixed an issue where if a pack README.md did not exist it could cause an error in the validation process.
* Fixed an issue where the *--name* was incorrectly required in the **init** command.
* Adding the option to run **validate** on a specific path while using git (*-i* & *-g*).
* The **format** command will now change UUIDs in .yml and .json files to their respective content entity name.
* Added a playbook validation to check if a task sub playbook exists in the id set in the **validate** command.
* Added the option to add new tags/usecases to the approved list and to the pack metadata on the same pull request.
* Fixed an issue in **test_content** where when different servers ran tests for the same integration, the server URL parameters were not set correctly.
* Added a validation in the **validate** command to ensure that the ***endpoint*** command is configured correctly in yml file.
* Added a warning when pack_metadata's description field is longer than 130 characters.
* Fixed an issue where a redundant print occurred on release notes validation.
* Added new validation in the **validate** command to ensure that the minimal fromVersion in a widget of type metrics will be 6.2.0.
* Added the *--release-notes* flag to demisto-sdk to get the current version release notes entries.

## 1.4.2

* Added to `pylint` summary an indication if a test was skipped.
* Added to the **init** command the option to specify fromversion.
* Fixed an issue where running **init** command without filling the metadata file.
* Added the *--docker-timeout* flag in the **lint** command to control the request timeout for the Docker client.
* Fixed an issue where **update-release-notes** command added only one docker image release notes entry for release notes file, and not for every entity whom docker image was updated.
* Added a validation to ensure that incident/indicator fields names starts with their pack name in the **validate** command. (Checked only for new files and only when using git *-g*)
* Updated the **find-dependencies** command to return the 'dependencies' according the layout type ('incident', 'indicator').
* Enhanced the "vX" display name validation for scripts and integrations in the **validate** command to check for every versioned script or integration, and not only v2.
* Added the *--fail-duplicates* flag for the **create-id-set** command which will fail the command if duplicates are found.
* Added to the **generate-docs** command automatic addition to git when a new readme file is created.

## 1.4.1

* When in private repo without `DEMSITO_SDK_GITHUB_TOKEN` configured, get_remote_file will take files from the local origin/master.
* Enhanced the **unify** command when giving input of a file and not a directory return a clear error message.
* Added a validation to ensure integrations are not skipped and at least one test playbook is not skipped for each integration or script.
* Added to the Content Tests support for `context_print_dt`, which queries the incident context and prints the result as a json.
* Added new validation for the `xsoar_config.json` file in the **validate** command.
* Added a version differences section to readme in **generate-docs** command.
* Added the *--docs-format* flag in the **integration-diff** command to get the output in README format.
* Added the *--input-old-version* and *--skip-breaking-changes* flags in the **generate-docs** command to get the details for the breaking section and to skip the breaking changes section.

## 1.4.0

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

## 1.3.9

* Added a validation verifying that the pack's README.md file is not equal to pack description.
* Fixed an issue where the **Assume yes** flag did not work properly for some entities in the **format** command.
* Improved the error messages for separators in folder and file names in the **validate** command.
* Removed the **DISABLE_SDK_VERSION_CHECK** environment variable. To disable new version checks, use the **DEMISTO_SDK_SKIP_VERSION_CHECK** envirnoment variable.
* Fixed an issue where the demisto-sdk version check failed due to a rate limit.
* Fixed an issue with playbooks scheme validation.

## 1.3.8

* Updated the **secrets** command to work on forked branches.

## 1.3.7

* Added a validation to ensure correct image and description file names.
* Fixed an issue where the **validate** command failed when 'display' field in credentials param in yml is empty but 'displaypassword' was provided.
* Added the **integration-diff** command to check differences between two versions of an integration and to return a report of missing and changed elements in the new version.
* Added a validation verifying that the pack's README.md file is not missing or empty for partner packs or packs contains use cases.
* Added a validation to ensure that the integration and script folder and file names will not contain separators (`_`, `-`, ``).
* When formatting new pack, the **format** command will set the *fromversion* key to 5.5.0 in the new files without fromversion.

## 1.3.6

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

## 1.3.5

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

## 1.3.4

* Updated the **validate** command to check that the 'additionalinfo' field only contains the expected value for feed required parameters and not equal to it.
* Added a validation that community/partner details are not in the detailed description file.
* Added a validation that the Use Case tag in pack_metadata file is only used when the pack contains at least one PB, Incident Type or Layout.
* Added a validation that makes sure outputs in integrations are matching the README file when only README has changed.
* Added the *hidden* field to the integration schema.
* Fixed an issue where running **format** on a playbook whose `name` does not equal its `id` would cause other playbooks who use that playbook as a sub-playbook to fail.
* Added support for local custom command configuration file `.demisto-sdk-conf`.
* Updated the **format** command to include an update to the description file of an integration, to remove community/partner details.

## 1.3.3

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

## 1.3.2

* Updated the format of the outputs when using the *--json-file* flag to create a JSON file output for the **validate** and **lint** commands.
* Added the **doc-review** command to check spelling in .md and .yml files as well as a basic release notes review.
* Added a validation that a pack's display name does not already exist in content repository.
* Fixed an issue where the **validate** command failed to detect duplicate params in an integration.
* Fixed an issue where the **validate** command failed to detect duplicate arguments in a command in an integration.

## 1.3.1

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

## 1.3.0

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

## 1.2.19

* Fixed an issue where merge id_set was not updated to work with the new entity of Packs.
* Added a validation that the playbook's version matches the version of its sub-playbooks, scripts, and integrations.

## 1.2.18

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

## 1.2.17

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

## 1.2.16

* Added allowed ignore errors to the *IDSetValidator*.
* Fixed an issue where an irrelevant id_set validation ran in the **validate** command when using the *--id-set* flag.
* Fixed an issue were **generate-docs** command has failed if a command did not exist in commands permissions file.
* Improved a **validate** command message for missing release notes of api module dependencies.

## 1.2.15

* Added the *ID101* to the allowed ignored errors.

## 1.2.14

* SDK repository is now mypy check_untyped_defs complaint.
* The lint command will now ignore the unsubscriptable-object (E1136) pylint error in dockers based on python 3.9 - this will be removed once a new pylint version is released.
* Added an option for **format** to run on a whole pack.
* Added new validation of unimplemented commands from yml in the code to `XSOAR-linter`.
* Fixed an issue where Auto-Extract fields were only checked for newly added incident types in the **validate** command.
* Added a new warning validation of direct access to args/params dicts to `XSOAR-linter`.

## 1.2.13

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

## 1.2.12

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

## 1.2.11

* Fixed an issue where the ***generate-docs*** command reset the enumeration of line numbering after an MD table.
* Updated the **upload** command to support mappers.
* Fixed an issue where exceptions were no printed in the **format** while the *--verbose* flag is set.
* Fixed an issue where *--assume-yes* flag did not work in the **format** command when running on a playbook without a `fromversion` field.
* Fixed an issue where the **format** command would fail in case `conf.json` file was not found instead of skipping the update.
* Fixed an issue where integration with v2 were recognised by the `name` field instead of the `display` field in the **validate** command.
* Added a playbook validation to check if a task script exists in the id set in the **validate** command.
* Added new integration category `File Integrity Management` in the **validate** command.

## 1.2.10

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

## 1.2.9

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

## 1.2.8

* Added a new validation that checks in playbooks for the usage of `DeleteContext` in **validate** command.
* Fixed an issue in the **upload** command where it would try to upload content entities with unsupported versions.
* Added a new validation that checks in playbooks for the usage of specific instance in **validate** command.
* Added the **--staged** flag to **validate** command to run on staged files only.

## 1.2.7

* Changed input parameters in **find-dependencies** command.
  * Use ***-i, --input*** instead of ***-p, --path***.
  * Use ***-idp, --id-set-path*** instead of ***-i, --id-set-path***.
* Fixed an issue in the **unify** command where it crashed on an integration without an image file.
* Fixed an issue in the **format** command where unnecessary files were not skipped.
* Fixed an issue in the **update-release-notes** command where the *text* argument was not respected in all cases.
* Fixed an issue in the **validate** command where a warning about detailed description was given for unified or deprecated integrations.
* Improved the error returned by the **validate** command when running on files using the old format.

## 1.2.6

* No longer require setting `DEMISTO_README_VALIDATION` env var to enable README mdx validation. Validation will now run automatically if all necessary node modules are available.
* Fixed an issue in the **validate** command where the `--skip-pack-dependencies` would not skip id-set creation.
* Fixed an issue in the **validate** command where validation would fail if supplied an integration with an empty `commands` key.
* Fixed an issue in the **validate** command where validation would fail due to a required version bump for packs which are not versioned.
* Will use env var `DEMISTO_VERIFY_SSL` to determine if to use a secure connection for commands interacting with the Server when `--insecure` is not passed. If working with a local Server without a trusted certificate, you can set env var `DEMISTO_VERIFY_SSL=no` to avoid using `--insecure` on each command.
* Unifier now adds a link to the integration documentation to the integration detailed description.
* Fixed an issue in the **secrets** command where ignored secrets were not skipped.

## 1.2.5

* Added support for special fields: *defaultclassifier*, *defaultmapperin*, *defaultmapperout* in **download** command.
* Added -y option **format** command to assume "yes" as answer to all prompts and run non-interactively
* Speed up improvements for `validate` of README files.
* Updated the **format** command to adhere to the defined content schema and sub-schemas, aligning its behavior with the **validate** command.
* Added support for canvasContextConnections files in **format** command.

## 1.2.4

* Updated detailed description for community integrations.

## 1.2.3

* Fixed an issue where running **validate** failed on playbook with task that adds tags to the evidence data.
* Added the *displaypassword* field to the integration schema.
* Added new code validations to `XSOAR-linter`.
  * As warnings messages:
    * `demisto.params()` should be used only inside main function.
    * `demisto.args()` should be used only inside main function.
    * Functions args should have type annotations.
* Added `fromversion` field validation to test playbooks and scripts in **validate** command.

## 1.2.2

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

## 1.2.1

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

## 1.2.0

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

## 1.1.11

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

## 1.1.10

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

## 1.1.9

* Fixed an issue where **update-release-notes** command failed on invalid file types.

## 1.1.8

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

## 1.1.7

* Fixed an issue where running the **format** command on feed integrations removed the `defaultvalue` fields.
* Playbook branch marked with *skipunavailable* is now set as an optional dependency in the **find-dependencies** command.
* The **feedReputation** parameter can now be hidden in a feed integration.
* Fixed an issue where running the **unify** command on JS package failed.
* Added the *--no-update* flag to the **find-dependencies** command.
* Added the following validations in **validate** command:
  * Validating that a pack does not depend on NonSupported / Deprecated packs.

## 1.1.6

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

## 1.1.5

* Fixed an issue in **find-dependencies** command.
* **lint** command now verifies flake8 on CommonServerPython script.

## 1.1.4

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

## 1.1.3

* Added a validation for invalid id fields in indicators types files in **validate** command.
* Added default behavior for **update-release-notes** command.
* Fixed an error where README files were failing release notes validation.
* Updated format of generated release notes to be more user friendly.
* Improved error messages for the **update-release-notes** command.
* Added support for `Connections`, `Dashboards`, `Widgets`, and `Indicator Types` to **update-release-notes** command.
* **Validate** now supports scripts under the *TestPlaybooks* directory.
* Fixed an issue where **validate** did not support powershell files.

## 1.1.2

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

## 1.1.1

* fixed and issue where file types were not recognized correctly in **validate** command.
* Added better outputs for validate command.

## 1.1.0

* Fixed an issue where changes to only non-validated files would fail validation.
* Fixed an issue in **validate** command where moved files were failing validation for new packs.
* Fixed an issue in **validate** command where added files were failing validation due to wrong file type detection.
* Added support for new classifiers and mappers in **validate** command.
* Removed support of old RN format validation.
* Updated **secrets** command output format.
* Added support for error ignore on deprecated files in **validate** command.
* Improved errors outputs in **validate** command.
* Added support for linting an entire pack.

## 1.0.9

* Fixed a bug where misleading error was presented when pack name was not found.
* **Update-release-notes** now detects added files for packs with versions.
* Readme files are now ignored by **update-release-notes** and validation of release notes.
* Empty release notes no longer cause an uncaught error during validation.

## 1.0.8

* Changed the output format of demisto-sdk secrets.
* Added a validation that checkbox items are not required in integrations.
* Added pack release notes generation and validation.
* Improved pack metadata validation.
* Fixed an issue in **validate** where renamed files caused an error

## 1.0.4

* Fix the **format** command to update the `id` field to be equal to `details` field in indicator-type files, and to `name` field in incident-type & dashboard files.
* Fixed a bug in the **validate** command for layout files that had `sortValues` fields.
* Fixed a bug in the **format** command where `playbookName` field was not always present in the file.
* Fixed a bug in the **format** command where indicatorField wasn't part of the SDK schemas.
* Fixed a bug in **upload** command where created unified docker45 yml files were not deleted.
* Added support for IndicatorTypes directory in packs (for `reputation` files, instead of Misc).
* Fixed parsing playbook condition names as string instead of boolean in **validate** command
* Improved image validation in YAML files.
* Removed validation for else path in playbook condition tasks.

## 1.0.3

* Fixed a bug in the **format** command where comments were being removed from YAML files.
* Added output fields: *file_path* and *kind* for layouts in the id-set.json created by **create-id-set** command.
* Fixed a bug in the **create-id-set** command Who returns Duplicate for Layouts with a different kind.
* Added formatting to **generate-docs** command results replacing all `<br>` tags with `<br/>`.
* Fixed a bug in the **download** command when custom content contained not supported content entity.
* Fixed a bug in **format** command in which boolean strings  (e.g. 'yes' or 'no') were converted to boolean values (e.g. 'True' or 'False').
* **format** command now removes *sourceplaybookid* field from playbook files.
* Fixed a bug in **generate-docs** command in which integration dependencies were not detected when generating documentation for a playbook.

## 1.0.1

* Fixed a bug in the **unify** command when output path was provided empty.
* Improved error message for integration with no tests configured.
* Improved the error message returned from the **validate** command when an integration is missing or contains malformed fetch incidents related parameters.
* Fixed a bug in the **create** command where a unified YML with a docker image for 4.5 was copied incorrectly.
* Missing release notes message are now showing the release notes file path to update.
* Fixed an issue in the **validate** command in which unified YAML files were not ignored.
* File format suggestions are now shown in the relevant file format (JSON or YAML).
* Changed Docker image validation to fail only on non-valid ones.
* Removed backward compatibility validation when Docker image is updated.

## 1.0.0

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

## 0.5.2

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

## 0.5.0

[PyPI History][1]

[1]: https://pypi.org/project/demisto-sdk/#history

## 0.4.9

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

## 0.4.8

* Added the *max* field to the Playbook schema, allowing to define it in tasks loop.
* Fixed an issue in *validate* where Condition branches checks were case sensitive.

## 0.4.7

* Added the *slareminder* field to the Playbook schema.
* Added the *common_server*, *demisto_mock* arguments to the *init* command.
* Fixed an issue in *generate-docs* where the general section was not being generated correctly.
* Fixed an issue in *validate* where Incident type validation failed.

## 0.4.6

* Fixed an issue where the *validate* command did not identify CHANGELOG in packs.
* Added a new command, *id-set* to create the id set - the content dependency tree by file IDs.

## 0.4.5

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

## 0.4.4

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

## 0.4.3

* Fixed an issue where the incident and indicator field BC check failed.
* Support for linting and unit testing PowerShell integrations.

## 0.4.2

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

## 0.3.10

* Added a BC check for incident fields - changing from version is not allowed.
* Fixed an issue in create-content-artifacts where scripts in Packs in TestPlaybooks dir were copied with a wrong prefix.

## 0.3.9

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

## 0.3.8

* Fixed an issue where *create-content-artifact* was not loading the data in the yml correctly.
* Fixed an issue where *unify* broke long lines in script section causing syntax errors

## 0.3.7

* Added *generate-docs* command to generate documentation file for integration, playbook or script.
* Fixed an issue where *unify* created a malformed integration yml.
* Fixed an issue where demisto-sdk **init** creates unit-test file with invalid import.

## 0.3.6

* Fixed an issue where demisto-sdk **validate** failed on modified scripts without error message.

## 0.3.5

* Fixed an issue with docker tag validation for integrations.
* Restructured repo source code.

## 0.3.4

* Saved failing unit tests as a file.
* Fixed an issue where "_test" file for scripts/integrations created using **init** would import the "HelloWorld" templates.
* Fixed an issue in demisto-sdk **validate** - was failing on backward compatiblity check
* Fixed an issue in demisto-sdk **secrets** - empty line in .secrets-ignore always made the secrets check to pass
* Added validation for docker image inside integrations and scripts.
* Added --use-git flag to **format** command to format all changed files.
* Fixed an issue where **validate** did not fail on dockerimage changes with bc check.
* Added new flag **--ignore-entropy** to demisto-sdk **secrets**, this will allow skip entropy secrets check.
* Added --outfile to **lint** to allow saving failed packages to a file.

## 0.3.3

* Added backwards compatibility break error message.
* Added schema for incident types.
* Added **additionalinfo** field to as an available field for integration configuration.
* Added pack parameter for **init**.
* Fixed an issue where error would appear if name parameter is not set in **init**.

## 0.3.2

* Fixed the handling of classifier files in **validate**.

## 0.3.1

* Fixed the handling of newly created reputation files in **validate**.
* Added an option to perform **validate** on a specific file.

## 0.3.0

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

## 0.2.6

* Fixed an issue with locating release notes for beta integrations in **validate**.

## 0.2.5

* Fixed an issue with locating release notes for beta integrations in **validate**.

## 0.2.4

* Adding image validation to Beta_Integration and Packs in **validate**.

## 0.2.3

* Adding Beta_Integration to the structure validation process.
* Fixing bug where **validate** did checks on TestPlaybooks.
* Added requirements parameter to **lint**.

## 0.2.2

* Fixing bug where **lint** did not return exit code 1 on failure.
* Fixing bug where **validate** did not print error message in case no release notes were give.

## 0.2.1

* **Validate** now checks that the id and name fields are identical in yml files.
* Fixed a bug where sdk did not return any exit code.

## 0.2.0

* Added Release Notes Validator.
* Fixed the Unifier selection of your python file to use as the code.
* **Validate** now supports Indicator fields.
* Fixed a bug where **validate** and **secrets** did not return exit code 1 on failure.
* **Validate** now runs on newly added scripts.

## 0.1.8

* Added support for `--version`.
* Fixed an issue in file_validator when calling `checked_type` method with script regex.

## 0.1.2

* Restructuring validation to support content packs.
* Added secrets validation.
* Added content bundle creation.
* Added lint and unit test run.

## 0.1.1

* Added new logic to the unifier.
* Added detailed README.
* Some small adjustments and fixes.

## 0.1.0

Capabilities:

* **Extract** components(code, image, description etc.) from a Demisto YAML file into a directory.
* **Unify** components(code, image, description etc.) to a single Demisto YAML file.
* **Validate** Demisto content files.
