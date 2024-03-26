from typing import List

from packaging.version import Version

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.logger import logger

FROM_VERSION_PRE_PROCESS_RULES = "6.5.0"


class PreProcessRuleValidator(ContentEntityValidator):
    def __init__(
        self,
        structure_validator=True,
        ignored_errors=False,
        json_file_path=None,
        **kwargs
    ):
        super().__init__(
            structure_validator, ignored_errors, json_file_path=json_file_path, **kwargs
        )
        self.from_version = self.current_file.get("fromVersion")
        self.to_version = self.current_file.get("toVersion")

    def is_valid_pre_process_rule(
        self, validate_rn=True, id_set_file=None, is_ci=False
    ) -> bool:
        """Check whether the pre_process_rules is valid or not.

        Returns:
            bool. Whether the pre_process_rules is valid or not
        """
        validations: List = [
            self.is_valid_version(),
            self.is_valid_from_version(),
        ]
        if id_set_file:
            validations.extend(
                [
                    self.is_script_exists(id_set_file=id_set_file, is_ci=is_ci),
                    self.are_incident_fields_exist(
                        id_set_file=id_set_file, is_ci=is_ci
                    ),
                ]
            )
        else:
            logger.info(
                "[yellow]Skipping PreProcessRule id_set validations. Could not read id_set.json.[/yellow]"
            )

        return all(validations)

    def is_valid_version(self) -> bool:
        """Checks if version field is valid. uses default method.

        Returns:
            bool. True if version is valid, else False.
        """
        return self._is_valid_version()

    @error_codes("PP100")
    def is_valid_from_version(self) -> bool:
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        if self.from_version:
            if Version(self.from_version) < Version(FROM_VERSION_PRE_PROCESS_RULES):
                (
                    error_message,
                    error_code,
                ) = Errors.invalid_from_version_in_pre_process_rules()
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False
        return True

    def get_all_incident_fields(self) -> List[str]:
        """Retrieved all mentioned Incident Fields from a ProProcessRule file.
        Sections to check: existingEventsFilters, newEventFilters, readyNewEventFilters

        Returns:
            List[str]. Of all the fields.
        """
        ret_value: List[str] = []

        for current_section in [
            "existingEventsFilters",
            "newEventFilters",
            "readyNewEventFilters",
        ]:
            ret_value.extend(self.get_all_incident_fields_in_section(current_section))

        return ret_value

    def get_all_incident_fields_in_section(self, section_name) -> List[str]:
        """Retrieved all mentioned Incident Fields from a specific section in a ProProcessRule file.

        Returns:
            List[str]. Of all the fields.
        """
        ret_value: List[str] = []

        for current_section_item in self.current_file.get(section_name, []):
            if isinstance(current_section_item, dict):
                current_section_item = list(current_section_item)
            for item in current_section_item:
                if item["left"]["isContext"]:
                    ret_value.append(item["left"]["value"]["simple"])
                if item["right"]["isContext"]:
                    right_value_simple = str(item["right"]["value"]["simple"])
                    right_value_simple = PreProcessRuleValidator.get_field_name(
                        right_value_simple
                    )
                    ret_value.append(right_value_simple)

        return ret_value

    @staticmethod
    def get_field_name(src: str) -> str:
        ret_value = src
        if ret_value.startswith("${"):
            ret_value = ret_value[2:]
        if ret_value.endswith("}"):
            ret_value = ret_value[:-1]
        return ret_value

    def is_script_exists(self, id_set_file, is_ci) -> bool:
        """Checks if scriptName is valid - exists in the content.

        Returns:
            bool. True if the script is valid, else False.
        """
        if not is_ci:
            return True

        script_name = self.current_file.get("scriptName", "")
        if not script_name:
            return True

        scripts = id_set_file["scripts", []]
        for current_script in scripts:
            script_id = list(current_script.keys())[0]
            if script_name == current_script[script_id]["name"]:
                return True

        return False

    @error_codes("PP102")
    def are_incident_fields_exist(self, id_set_file, is_ci) -> bool:
        """Checks if incident field is valid - exist in the content.

        Returns:
            bool. True if incident field is valid, else False.
        """
        if not is_ci:
            return True

        fields = id_set_file["IncidentFields"]
        id_set_fields = {list(field.keys())[0] for field in fields}

        pre_process_rule_fields = self.get_all_incident_fields()

        invalid_fields = set(pre_process_rule_fields) - id_set_fields
        if invalid_fields:
            error_message, error_code = Errors.unknown_fields_in_pre_process_rules(
                ", ".join(invalid_fields)
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True
