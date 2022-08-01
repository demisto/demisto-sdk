"""
This module is designed to validate the correctness of generic definition entities in content.
"""
import os

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.tools import get_files_in_dir

yaml = YAML_Handler()


class ModelingRuleValidator(ContentEntityValidator):
    """
    ModelingRuleValidator is designed to validate the correctness of the file structure we enter to content repo.
    """

    def __init__(self, structure_validator, ignored_errors=None, print_as_warnings=False, json_file_path=None):
        super().__init__(structure_validator, ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         json_file_path=json_file_path)
        self._is_valid = True

    def is_valid_file(self, validate_rn=True, is_new_file=False, use_git=False):
        """
        Check whether the modeling rule is valid or not
        Note: For now we return True regardless of the item content. More info:
        https://github.com/demisto/etc/issues/48151#issuecomment-1109660727
        """

        self.is_schema_file_exists()
        self.are_keys_empty_in_yml()
        self.is_valid_rule_names()

        return self._is_valid

    def is_valid_version(self):
        """
        May deleted or be edited in the future by the use of XSIAM new content
        """
        pass

    def is_schema_file_exists(self):
        # Gets the schema.json file from the modeling rule folder
        files_to_check = get_files_in_dir(os.path.dirname(self.file_path), ['json'], False)
        if not files_to_check:
            error_message, error_code = Errors.modeling_rule_missing_schema_file(self.file_path)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False
                return False
        return True

    def are_keys_empty_in_yml(self):
        """
        Check that the schema and rules keys are empty.
        """
        with open(self.file_path, 'r') as yf:
            yaml_obj = yaml.load(yf)

        # Check that the keys exists in yml
        if 'rules' in yaml_obj and 'schema' in yaml_obj:
            # Check that the following keys in the yml are empty
            if not yaml_obj['rules'] and not yaml_obj['schema']:
                return True
            else:
                error_message, error_code = Errors.modeling_rule_keys_not_empty()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    self._is_valid = False
                    return False

        # Case that we are missing those keys from the yml file
        error_message, error_code = Errors.modeling_rule_keys_are_missing()
        if self.handle_error(error_message, error_code, file_path=self.file_path):
            self._is_valid = False
            return False
        return True

    def is_valid_rule_names(self):
        """Check if the rule file names is valid"""
        # Gets all the files in the modeling rule folder
        files_to_check = get_files_in_dir(os.path.dirname(self.file_path), ['json', 'xif', 'yml'], False)
        integrations_folder = os.path.basename(os.path.dirname(self.file_path))
        invalid_files = []

        for file_path in files_to_check:
            file_name = os.path.basename(file_path)
            # The schema has _schema.json suffix whereas the integration only has the .suffix
            splitter = '_' if file_name.endswith('_schema.json') else '.'
            base_name = file_name.rsplit(splitter, 1)[0]

            if integrations_folder != base_name:
                invalid_files.append(file_name)

        if invalid_files:
            error_message, error_code = Errors.invalid_rule_name(invalid_files)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True
