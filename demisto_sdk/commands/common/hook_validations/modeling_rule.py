"""
This module is designed to validate the correctness of generic definition entities in content.
"""
import json
import os
import re

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import ContentEntityValidator
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
        self.schema_path = None
        self.schema_content = None
        self.xif_path = None
        self.set_files_info()

    def set_files_info(self):
        files = get_files_in_dir(os.path.dirname(self.file_path), ['json', 'xif'], False)
        for file in files:
            if file.endswith('_schema.json'):
                self.schema_path = file
                with open(file, 'r') as sf:
                    self.schema_content = json.load(sf)
            if file.endswith('.xif'):
                self.xif_path = file

    def is_valid_file(self, validate_rn=True, is_new_file=False, use_git=False):
        """
        Check whether the modeling rule is valid or not
        Note: For now we return True regardless of the item content. More info:
        https://github.com/demisto/etc/issues/48151#issuecomment-1109660727
        """

        self.is_schema_file_exists()
        self.are_keys_empty_in_yml()
        self.is_valid_rule_names()
        self.is_schema_types_valid()
        self.is_dataset_name_similar()
        self.is_files_naming_correct()
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

    @error_codes("MR104")
    def is_schema_types_valid(self):
        """
            Validates all types used in the schema file are valid, i.e. part of the list below.
        """
        valid_type = ['string', 'int', 'float', 'datetime', 'boolean']
        invalid_types = []
        if self.schema_content:
            attributes = list(self.schema_content.values())[0]
            for attr in attributes.values():
                type_to_validate = attr.get('type')
                if type_to_validate not in valid_type:
                    invalid_types.append(type_to_validate)

            if invalid_types:
                error_message, error_code = Errors.modeling_rule_schema_types_invalid(invalid_types)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    self._is_valid = False
                    return False
        return True

    @error_codes("MR105")
    def is_dataset_name_similar(self):
        """
            Validates the dataset name is the same in the xif file and in the schema file
        """

        def get_dataset_from_xif(xif_file_path):
            with open(xif_file_path, 'r') as xif_file:
                xif_content = xif_file.read()
                dataset = re.findall("dataset[ ]?=[ ]?([\"a-zA-Z_0-9]+)", xif_content)
                if dataset:
                    return [dataset_name.strip("\"") for dataset_name in dataset]
            return None

        xif_file_path = get_files_in_dir(os.path.dirname(self.file_path), ['xif'], False)
        if xif_file_path and self.schema_content:
            xif_datasets = get_dataset_from_xif(xif_file_path[0])
            schema_datasets = self.schema_content.keys()
            if len(xif_datasets) == len(schema_datasets) and len(xif_datasets) >= 1:
                all_exist = all(dataset in schema_datasets for dataset in xif_datasets)
                if all_exist:
                    return True

        error_message, error_code = Errors.modeling_rule_schema_xif_dataset_mismatch()
        if self.handle_error(error_message, error_code, file_path=self.file_path):
            self._is_valid = False
            return False

    @error_codes("BA120")
    def is_files_naming_correct(self):
        """
        Validates all file naming is as convention.
        """
        invalid_files = []
        if not self.validate_xsiam_content_item_title(self.file_path):
            invalid_files.append(self.file_path)
        if self.schema_path:
            if not self.validate_xsiam_content_item_title(self.schema_path):
                invalid_files.append(self.schema_path)
        if self.xif_path:
            if not self.validate_xsiam_content_item_title(self.xif_path):
                invalid_files.append(self.xif_path)
        if invalid_files:
            error_message, error_code = Errors.files_naming_wrong(invalid_files)
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
