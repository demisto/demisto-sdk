import json
import os
from typing import Any, Dict, Iterator, Tuple

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from jsonschema import Draft7Validator, ValidationError
from prettytable import PrettyTable


class XSOARConfigJsonValidator(BaseValidator):
    """XSOARConfigJsonValidator has been designed to make sure we are following the standards for the
    xsoar_config.json file.

    Attributes:
        _is_valid (bool): Whether the conf.json file current state is valid or not.
        config_json (dict): The data from the xsoar_config.json file.
        schema_json (dict): The data from the schema file.
    """

    def __init__(self, configuration_file_path, json_file_path=None,
                 ignored_errors=None, print_as_warnings=False, suppress_print=False):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print, json_file_path=json_file_path)
        self._is_valid = True
        self.configuration_file_path = configuration_file_path
        self.schema_path = os.path.normpath(os.path.join(__file__, '..', '..', 'schemas', 'xsoar_config.json'))
        self.config_json = self.load_configuration_file()
        self.schema_json = self.load_schema_file()

    def load_configuration_file(self) -> Dict[str, Any]:
        """Loads the configuration file for the schema validation.

        Returns:
            Dict[str, Any]. The contents of the configuration file.
        """
        try:
            with open(self.configuration_file_path, 'r') as f:
                config_json = json.load(f)
        except Exception:
            error_message, error_code = Errors.xsoar_config_file_is_not_json(self.configuration_file_path)
            if self.handle_error(error_message, error_code, file_path=self.configuration_file_path):
                self._is_valid = False

        return config_json

    def load_schema_file(self) -> Dict[str, Any]:
        """Loads the schema file for the schema validation.

        Returns:
            Dict[str, Any]. The contents of the schema file.
        """
        with open(self.schema_path, 'r') as f:
            schema_json = json.load(f)

        return schema_json

    @staticmethod
    def create_schema_validation_results_table(errors: Iterator[ValidationError]) -> Tuple[PrettyTable, bool]:
        """Parses the schema validation errors into a table.

        Args:
            errors (Iterator[ValidationError]): The errors that the validator found.

        Returns:
            PrettyTable. The parsed table containing the errors data.
            bool. Whether there were errors in the validation.
        """
        errors_table = PrettyTable()
        errors_table.field_names = ['', 'Error Message']

        errors_found = False
        for index, error in enumerate(errors):
            errors_table.add_row([index, error.message])
            errors_found = True

        return errors_table, errors_found

    def is_valid_xsoar_config_file(self):
        validator = Draft7Validator(schema=self.schema_json)
        errors = validator.iter_errors(self.config_json)

        errors_table, errors_found = self.create_schema_validation_results_table(errors)
        if errors_found:
            error_message, error_code = Errors.xsoar_config_file_malformed(
                self.configuration_file_path,
                self.schema_path,
                errors_table,
            )
            if self.handle_error(error_message, error_code, file_path=self.configuration_file_path):
                self._is_valid = False

        return self._is_valid
