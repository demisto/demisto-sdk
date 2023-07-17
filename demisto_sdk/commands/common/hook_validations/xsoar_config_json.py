import os
from typing import Any, Dict, Iterator, Optional, Tuple

from jsonschema import Draft7Validator, ValidationError
from prettytable import PrettyTable

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.hook_validations.base_validator import (
    BaseValidator,
    error_codes,
)
from demisto_sdk.commands.common.tools import get_dict_from_file


class XSOARConfigJsonValidator(BaseValidator):
    """XSOARConfigJsonValidator has been designed to make sure we are following the standards for the
    xsoar_config.json file.

    Attributes:
        _is_valid (bool): Whether the conf.json file current state is valid or not.
        configuration_file_path (dict): The path to the xsoar_config.json file.
        schema_path (dict): The data to the schema file.
        configuration_json (dict): The data from the xsoar_config.json file.
        schema_json (dict): The data from the schema file.
    """

    def __init__(
        self,
        configuration_file_path,
        json_file_path=None,
        ignored_errors=None,
        specific_validations=None,
    ):
        super().__init__(
            ignored_errors=ignored_errors,
            json_file_path=json_file_path,
            specific_validations=specific_validations,
        )
        self._is_valid = True
        self.configuration_file_path = configuration_file_path
        self.schema_path = os.path.normpath(
            os.path.join(__file__, "..", "..", "schemas", "xsoar_config.json")
        )
        self.configuration_json = self.load_xsoar_configuration_file()
        self.schema_json, _ = get_dict_from_file(self.schema_path)

    def load_xsoar_configuration_file(self) -> Optional[Dict[str, Any]]:
        """Loads the configuration file for the schema validation.

        Returns:
            Dict[str, Any]. The contents of the configuration file.
        """
        try:
            with open(self.configuration_file_path) as f:
                config_json = json.load(f)
        except Exception:
            error_message, error_code = Errors.xsoar_config_file_is_not_json(
                self.configuration_file_path
            )
            if self.handle_error(
                error_message, error_code, file_path=self.configuration_file_path
            ):
                self._is_valid = False
            return None

        return config_json

    @staticmethod
    def create_schema_validation_results_table(
        errors: Iterator[ValidationError],
    ) -> Tuple[PrettyTable, bool]:
        """Parses the schema validation errors into a table.

        Args:
            errors (Iterator[ValidationError]): The errors that the validator found.

        Returns:
            PrettyTable. The parsed table containing the errors data.
            bool. Whether there were errors in the validation.
        """
        errors_table = PrettyTable()
        errors_table.field_names = ["", "Error Message"]

        errors_found = False
        for index, error in enumerate(errors):
            errors_table.add_row([index, error.message])
            errors_found = True

        return errors_table, errors_found

    @error_codes("XC101")
    def is_valid_xsoar_config_file(self):
        """Runs the schema validation on the configuration data, with the schema data.

        Returns:
            bool. Whether the configuration file's schema is valid or not.
        """
        validator = Draft7Validator(schema=self.schema_json)
        errors = validator.iter_errors(self.configuration_json)

        errors_table, errors_found = self.create_schema_validation_results_table(errors)
        if errors_found:
            error_message, error_code = Errors.xsoar_config_file_malformed(
                self.configuration_file_path,
                self.schema_path,
                errors_table,
            )
            if self.handle_error(
                error_message, error_code, file_path=self.configuration_file_path
            ):
                self._is_valid = False

        return self._is_valid
