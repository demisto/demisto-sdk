from demisto_sdk.commands.common.hook_validations.base_validator import BaseValidator
from demisto_sdk.commands.common.tools import print_error


class DashboardValidator(BaseValidator):
    @staticmethod
    def get_widgets_from_dashboard(dashboard):
        # type: () -> list
        layout_of_dashboard: list = dashboard.get('layout', [])
        widgets = []
        if layout_of_dashboard:
            widgets = [item.get('widget') for item in layout_of_dashboard]
        return widgets

    def is_valid_dashboard(self, validate_rn=True):
        # type: () -> bool
        """Check whether the dashboard is valid or not.

        Returns:
            bool. Whether the dashboard is valid or not
        """
        is_dashboard_valid = [
            super().is_valid_file(validate_rn),
            self.is_valid_version()
        ]

        # check only on added files
        if not self.old_file:
            is_dashboard_valid = all([
                is_dashboard_valid,
                self.is_id_equals_name()
            ])

        return is_dashboard_valid

    def is_valid_version(self):
        # type: () -> bool
        """Return if version is valid. uses default method.

        Returns:
            True if version is valid, else False.
        """
        return self._is_valid_version()

    def is_id_equals_name(self):
        # type: () -> bool
        """Check whether the dashboard ID is equal to its name.

        Returns:
            bool. Whether the file id equals to its name
        """
        return super(DashboardValidator, self)._is_id_equals_name('dashboard')

    def contains_forbidden_fields(self):
        # type: () -> bool
        """Return if root and widgets exclude the unnecessary fields.

        Returns:
            True if exclude, else False.
        """
        error_msg = ""
        is_valid = True
        fields_to_exclude = ['system', 'isCommon', 'shared', 'owner',
                             'sortValues', 'vcShouldIgnore', 'commitMessage', 'shouldCommit']

        widgets = self.get_widgets_from_dashboard(self.current_file)

        for field in fields_to_exclude:
            if self.current_file.get(field) is not None:
                is_valid = False
                error_msg += f'{self.file_path}: the field {field} needs to be removed.\n'
            # iterate over the widgets if exist
            if widgets:
                for widget in widgets:
                    if widget.get(field):
                        is_valid = False
                        error_msg += f'The field {field} needs to be removed from the widget: {widget}.\n'
        if error_msg:
            print_error(error_msg)
        return is_valid

    def is_including_fields(self):
        # type: () -> bool
        """Return if root and inner widgets includes the necessary fields.

        Returns:
            True if include, else False.
        """
        error_msg = ""
        is_valid = True
        fields_to_include = ['fromDate', 'toDate', 'fromDateLicense']

        widgets = self.get_widgets_from_dashboard(self.current_file)

        for field in fields_to_include:
            if not self.current_file.get(field):
                is_valid = False
                error_msg += f'{self.file_path}: the field {field} needs to be included. Please add it.\n'
            # iterate over the widgets if exist
            if widgets:
                for widget in widgets:
                    if not widget.get(field):
                        is_valid = False
                        widget_name = widget.get("name")
                        error_msg += f'The field {field} needs to be included in the widget: {widget_name}.' \
                                     f' Please add it.\n'
        if error_msg:
            print_error(error_msg)
        return is_valid
