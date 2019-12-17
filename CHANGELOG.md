# Changelog

[PyPI History][1]

[1]: https://pypi.org/project/demisto-sdk/#history

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
