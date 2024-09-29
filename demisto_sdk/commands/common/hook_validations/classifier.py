from packaging.version import Version

from demisto_sdk.commands.common.constants import LAYOUT_AND_MAPPER_BUILT_IN_FIELDS
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    get_all_incident_and_indicator_fields_from_id_set,
)
from demisto_sdk.commands.common.update_id_set import BUILT_IN_FIELDS

FROM_VERSION_FOR_NEW_CLASSIFIER = "6.0.0"
TO_VERSION_FOR_OLD_CLASSIFIER = "5.9.9"
CLASSIFICATION_TYPE = "classification"


class ClassifierValidator(ContentEntityValidator):
    def __init__(
        self,
        structure_validator,
        new_classifier_version=True,
        ignored_errors=None,
        is_circle=False,
        json_file_path=None,
    ):
        super().__init__(
            structure_validator,
            ignored_errors=ignored_errors,
            json_file_path=json_file_path,
        )
        self.new_classifier_version = new_classifier_version
        self.from_version = ""
        self.to_version = ""
        self.is_circle = is_circle

    def is_valid_classifier(self, validate_rn=True, id_set_file=None, is_circle=False):
        """Checks whether the classifier is valid or not.

        Returns:
            bool. True if classifier is valid, else False.
        """
        if not self.new_classifier_version:
            return all(
                [
                    super().is_valid_file(validate_rn),
                    self.is_valid_version(),
                    self.is_valid_from_version(),
                    self.is_valid_to_version(),
                    self.is_to_version_higher_from_version(),
                    self.is_valid_type(),
                    self.is_incident_field_exist(id_set_file, is_circle),
                ]
            )

        return all(
            [
                super().is_valid_file(validate_rn),
                self.is_valid_version(),
                self.is_valid_from_version(),
                self.is_valid_to_version(),
                self.is_to_version_higher_from_version(),
                self.is_valid_type(),
                self.is_id_equals_name(),
            ]
        )

    def is_id_equals_name(self):
        """Check whether the classifier's ID is equal to its name

        Returns:
            bool. True if valid, and False otherwise.
        """
        return super()._is_id_equals_name("classifier")

    def is_valid_version(self):
        """Checks if version field is valid. uses default method.

        Returns:
            bool. True if version is valid, else False.
        """
        return self._is_valid_version()

    @error_codes("CL102,CL103,CL104")
    def is_valid_from_version(self):
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        from_version = self.current_file.get(
            "fromVersion", ""
        ) or self.current_file.get("fromversion", "")
        if from_version:
            self.from_version = from_version
            if self.new_classifier_version:
                if Version(from_version) < Version(FROM_VERSION_FOR_NEW_CLASSIFIER):
                    (
                        error_message,
                        error_code,
                    ) = Errors.invalid_from_version_in_new_classifiers()
                    if self.handle_error(
                        error_message,
                        error_code,
                        file_path=self.file_path,
                        suggested_fix=Errors.suggest_fix(self.file_path),
                    ):
                        return False
            else:
                if Version(from_version) >= Version(FROM_VERSION_FOR_NEW_CLASSIFIER):
                    (
                        error_message,
                        error_code,
                    ) = Errors.invalid_from_version_in_old_classifiers()
                    if self.handle_error(
                        error_message,
                        error_code,
                        file_path=self.file_path,
                        suggested_fix=Errors.suggest_fix(self.file_path),
                    ):
                        return False

        elif not from_version and self.new_classifier_version:
            error_message, error_code = Errors.missing_from_version_in_new_classifiers()
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_fix(self.file_path),
            ):
                return False
        return True

    @error_codes("CL100,CL101,CL105")
    def is_valid_to_version(self):
        """Checks if to version field is valid.

        Returns:
            bool. True if to version filed is valid, else False.
        """
        to_version = self.current_file.get("toVersion", "") or self.current_file.get(
            "toversion", ""
        )
        if to_version:
            self.to_version = to_version
            if self.new_classifier_version:
                if Version(to_version) <= Version(FROM_VERSION_FOR_NEW_CLASSIFIER):
                    (
                        error_message,
                        error_code,
                    ) = Errors.invalid_to_version_in_new_classifiers()
                    if self.handle_error(
                        error_message, error_code, file_path=self.file_path
                    ):
                        return False
            else:
                if Version(to_version) > Version(TO_VERSION_FOR_OLD_CLASSIFIER):
                    (
                        error_message,
                        error_code,
                    ) = Errors.invalid_to_version_in_old_classifiers()
                    if self.handle_error(
                        error_message,
                        error_code,
                        file_path=self.file_path,
                        suggested_fix=Errors.suggest_fix(self.file_path),
                    ):
                        return False

        elif not to_version and not self.new_classifier_version:
            error_message, error_code = Errors.missing_to_version_in_old_classifiers()
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_fix(self.file_path),
            ):
                return False
        return True

    @error_codes("CL106")
    def is_to_version_higher_from_version(self):
        """Checks if to version field is higher than from version field.

        Returns:
            bool. True if to version field is higher than from version field, else False.
        """
        if self.to_version and self.from_version:
            if Version(self.to_version) <= Version(self.from_version):
                error_message, error_code = Errors.from_version_higher_to_version()
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False
        return True

    @error_codes("CL107")
    def is_valid_type(self):
        """Checks if type field is valid.

        Returns:
            bool. True if type field is valid, else False.
        """
        if (
            self.new_classifier_version
            and self.current_file.get("type") != CLASSIFICATION_TYPE
        ):
            error_message, error_code = Errors.invalid_type_in_new_classifiers()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("MP106")
    def is_incident_field_exist(self, id_set_file, is_circle) -> bool:
        """Checks if classifier incident fields is exist in content repo, this validation is only for old classifiers.

        Returns:
            bool. True if incident fields is valid - exist in content repo, else False.
        """
        if not is_circle:
            return True

        if not id_set_file:
            logger.info(
                "<yellow>Skipping classifier incident field validation. Could not read id_set.json.</yellow>"
            )
            return True

        built_in_fields = [
            field.lower() for field in BUILT_IN_FIELDS
        ] + LAYOUT_AND_MAPPER_BUILT_IN_FIELDS
        content_incident_fields = get_all_incident_and_indicator_fields_from_id_set(
            id_set_file, "old classifier"
        )

        invalid_inc_fields_list = []
        mapper = self.current_file.get("mapping", {})
        for incident_type, mapping in mapper.items():
            incident_fields = mapping.get("internalMapping") or {}

            for inc_name, _ in incident_fields.items():
                if (
                    inc_name not in content_incident_fields
                    and inc_name.lower() not in built_in_fields
                ):
                    invalid_inc_fields_list.append(inc_name)

        if invalid_inc_fields_list:
            error_message, error_code = Errors.invalid_incident_field_in_mapper(
                invalid_inc_fields_list
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True
