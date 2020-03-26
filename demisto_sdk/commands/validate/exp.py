from file_validator import FilesValidator

base = FilesValidator(use_git=True, validate_conf_json=False)
# test = base.get_content_release_identifier()

base.validate_against_previous_version()