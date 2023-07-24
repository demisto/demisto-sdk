from packaging.version import Version

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)


class WidgetValidator(ContentEntityValidator):
    WIDGET_TYPE_METRICS_MIN_VERSION = "6.2.0"

    def is_valid_version(self):
        """Return if version is valid. uses default method.

        Returns:
            True if version is valid, else False.
        """
        return self._is_valid_version()

    def is_valid_file(self, validate_rn: bool = False):
        """
        Check whether the widget is valid or not.

        Args:
            validate_rn (bool): Whether to validate release notes (changelog) or not.

        Returns:
            bool: True if widget is valid, False otherwise.
        """
        answers = [
            super().is_valid_file(validate_rn),
            self._is_valid_fromversion(),
        ]

        return all(answers)

    @error_codes("WD102")
    def _is_valid_fromversion(self):
        """
        Check whether the fromVersion field is valid.

        Return:
            bool: True if is valid, False otherwise.
        """

        widget_data_type = self.current_file.get("dataType", "")
        widget_from_version = self.current_file.get("fromVersion", "")

        if widget_data_type == "metrics" and Version(widget_from_version) < Version(
            self.WIDGET_TYPE_METRICS_MIN_VERSION
        ):
            error_message, error_code = Errors.invalid_fromversion_for_type_metrics()
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_fix(self.file_path),
            ):
                return False

        return True
