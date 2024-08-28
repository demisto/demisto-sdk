from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.logger import logger


class DashboardValidator(ContentEntityValidator):
    @staticmethod
    def get_widgets_from_dashboard(dashboard) -> list:
        layout_of_dashboard: list = dashboard.get("layout", [])
        widgets = []
        if layout_of_dashboard:
            widgets = [item.get("widget") for item in layout_of_dashboard]
        return widgets

    def is_valid_dashboard(self, validate_rn: bool = True) -> bool:
        """Check whether the dashboard is valid or not.

        Returns:
            bool. Whether the dashboard is valid or not
        """
        is_dashboard_valid = super().is_valid_file(validate_rn)

        # check only on added files
        if not self.old_file:
            is_dashboard_valid = all([is_dashboard_valid, self.is_id_equals_name()])

        return is_dashboard_valid

    def is_valid_version(self) -> bool:
        """Return if version is valid. uses default method.

        Returns:
            True if version is valid, else False.
        """
        return self._is_valid_version()

    def is_id_equals_name(self) -> bool:
        """Check whether the dashboard ID is equal to its name.

        Returns:
            bool. Whether the file id equals to its name
        """
        return super()._is_id_equals_name("dashboard")

    @error_codes("DA100,WD100")
    def contains_forbidden_fields(self) -> bool:
        """Return if root and widgets exclude the unnecessary fields.

        Returns:
            True if exclude, else False.
        """
        error_msg = ""
        is_valid = True
        fields_to_exclude = [
            "system",
            "isCommon",
            "shared",
            "owner",
            "sortValues",
            "vcShouldIgnore",
            "commitMessage",
            "shouldCommit",
        ]

        widgets = self.get_widgets_from_dashboard(self.current_file)

        for field in fields_to_exclude:
            if self.current_file.get(field) is not None:
                error_message, error_code = Errors.remove_field_from_dashboard(field)
                formatted_message = self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                )
                if formatted_message:
                    is_valid = False
                    error_msg += formatted_message
            # iterate over the widgets if exist
            if widgets:
                for widget in widgets:
                    if widget.get(field):
                        error_message, error_code = Errors.remove_field_from_widget(
                            field, widget
                        )
                        formatted_message = self.handle_error(
                            error_message,
                            error_code,
                            file_path=self.file_path,
                        )
                        if formatted_message:
                            is_valid = False
                            error_msg += formatted_message
        if error_msg:
            logger.info(f"<red>{error_msg}</red>")
        return is_valid

    @error_codes("DA101,WD101")
    def is_including_fields(self) -> bool:
        """Return if root and inner widgets includes the necessary fields.

        Returns:
            True if include, else False.
        """
        error_msg = ""
        is_valid = True
        fields_to_include = ["fromDate", "toDate", "fromDateLicense"]

        widgets = self.get_widgets_from_dashboard(self.current_file)

        for field in fields_to_include:
            if not self.current_file.get(field):
                error_message, error_code = Errors.include_field_in_dashboard(field)
                formatted_message = self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                )
                if formatted_message:
                    is_valid = False
                    error_msg += formatted_message
            # iterate over the widgets if exist
            if widgets:
                for widget in widgets:
                    if not widget.get(field):
                        widget_name = widget.get("name")
                        error_message, error_code = Errors.include_field_in_widget(
                            field, widget_name
                        )
                        formatted_message = self.handle_error(
                            error_message,
                            error_code,
                            file_path=self.file_path,
                        )
                        if formatted_message:
                            is_valid = False
                            error_msg += formatted_message
        if error_msg:
            logger.error(f"<red>{error_msg}</red>")
        return is_valid
