"""
This module is designed to validate the correctness of generic definition entities in content.
"""
import os
import re
from pathlib import Path
from typing import List

from demisto_sdk.commands.common.constants import (
    ASSETS_MODELING_RULE,
    MODELING_RULE,
    FileType,
)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.tools import get_files_in_dir


class ModelingRuleValidator(ContentEntityValidator):
    """
    ModelingRuleValidator is designed to validate the correctness of the file structure we enter to content repo.
    """

    MIN_FROMVERSION_REQUIRES_TESTDATA = "6.10.0"

    def __init__(
        self,
        structure_validator,
        ignored_errors=None,
        json_file_path=None,
    ):
        super().__init__(
            structure_validator,
            ignored_errors=ignored_errors,
            json_file_path=json_file_path,
        )
        rule_type = (
            MODELING_RULE
            if structure_validator.file_type
            in [
                FileType.MODELING_RULE,
                FileType.MODELING_RULE_SCHEMA,
                FileType.MODELING_RULE_XIF,
                FileType.MODELING_RULE_TEST_DATA,
            ]
            else ASSETS_MODELING_RULE
        )
        self._is_valid = self.is_valid_rule_suffix(rule_type)
        self.schema_path = None
        self.schema_content = None
        self.xif_path = None
        self.set_files_info()

    def set_files_info(self):
        files = get_files_in_dir(
            os.path.dirname(self.file_path), ["json", "xif"], False
        )
        for file in files:
            if file.endswith("_schema.json"):
                self.schema_path = file
                with open(file) as sf:
                    self.schema_content = json.load(sf)
            if file.endswith(".xif"):
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
        self.dataset_name_matches_in_xif_and_schema()

        return self._is_valid

    def is_valid_version(self):
        """
        May deleted or be edited in the future by the use of XSIAM new content
        """
        pass

    def is_schema_file_exists(self):
        # Gets the schema.json file from the modeling rule folder
        schema_files = list(
            Path(self.file_path).parent.glob(
                "*_[sS][cC][hH][eE][mM][aA].[jJ][sS][oO][nN]"
            )
        )
        has_schema = len(schema_files) > 0
        if not has_schema:
            error_message, error_code = Errors.modeling_rule_missing_schema_file(
                self.file_path
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False
                return has_schema
        return has_schema

    @error_codes("MR106")
    def is_schema_types_valid(self):
        """
        Validates all types used in the schema file are valid, i.e. part of the list below.
        """
        valid_types = {"string", "int", "float", "datetime", "boolean"}
        invalid_types = []
        if self.schema_content:
            for dataset in self.schema_content:
                attributes = self.schema_content.get(dataset)
                for attr in attributes.values():
                    type_to_validate = attr.get("type")
                    if type_to_validate not in valid_types:
                        invalid_types.append(type_to_validate)

            if invalid_types:
                error_message, error_code = Errors.modeling_rule_schema_types_invalid(
                    invalid_types
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    self._is_valid = False
                    return False
        return True

    @error_codes("MR107")
    def dataset_name_matches_in_xif_and_schema(self):
        """
        Validates the dataset name is the same in the xif file and in the schema file
        """

        def get_dataset_from_xif(xif_file_path: str) -> List[str]:
            with open(xif_file_path) as xif_file:
                xif_content = xif_file.read()
                dataset = re.findall('dataset[ ]?=[ ]?(["a-zA-Z_0-9]+)', xif_content)
            if dataset:
                return [dataset_name.strip('"') for dataset_name in dataset]
            return []

        xif_file_path = get_files_in_dir(
            os.path.dirname(self.file_path), ["xif"], False
        )
        if xif_file_path and self.schema_content:
            xif_datasets = set(get_dataset_from_xif(xif_file_path[0]))
            schema_datasets = self.schema_content.keys()
            if len(xif_datasets) == len(schema_datasets) and len(xif_datasets) >= 1:
                all_exist = all(dataset in schema_datasets for dataset in xif_datasets)
                if all_exist:
                    return True

        error_message, error_code = Errors.modeling_rule_schema_xif_dataset_mismatch()
        if self.handle_error(error_message, error_code, file_path=self.file_path):
            self._is_valid = False
            return False

    def are_keys_empty_in_yml(self):
        """
        Check that the schema and rules keys are empty.
        """
        with open(self.file_path) as yf:
            yaml_obj = yaml.load(yf)

        # Check that the keys exists in yml
        if "rules" in yaml_obj and "schema" in yaml_obj:
            # Check that the following keys in the yml are empty
            if not yaml_obj["rules"] and not yaml_obj["schema"]:
                return True
            else:
                error_message, error_code = Errors.modeling_rule_keys_not_empty()
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
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
        files_to_check = get_files_in_dir(
            os.path.dirname(self.file_path), ["json", "xif", "yml"], False
        )
        integrations_folder = Path(self.file_path).parent.name
        invalid_files = []

        for file_path in files_to_check:
            file_name = Path(file_path).name
            file_name_std = file_name.casefold()
            # The schema has _schema.json suffix and the testdata file has _testdata.json suffix
            # whereas the other content entity component files only has the .suffix
            splitter = (
                "_"
                if (
                    file_name_std.endswith("_schema.json")
                    or file_name_std.endswith("_testdata.json")
                )
                else "."
            )
            base_name = file_name.rsplit(splitter, 1)[0]

            if integrations_folder != base_name:
                invalid_files.append(file_name)

        if invalid_files:
            error_message, error_code = Errors.invalid_rule_name(invalid_files)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False
                return False

        return True
