from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.tools import print_error


class DashboardValidator(ContentEntityValidator):
    @staticmethod
    def get_widgets_from_dashboard(dashboard):
        # type: () -> list
        layout_of_dashboard: list = dashboard.get('layout', [])
        widgets = []
        if layout_of_dashboard:
            widgets = [item.get('widget') for item in layout_of_dashboard]
        return widgets

    def is_valid_dashboard(self, validate_rn=True):
        # type: (bool) -> bool
        """Check whether the dashboard is valid or not.

        Returns:
            bool. Whether the dashboard is valid or not
        """
        is_dashboard_valid = all([
            super().is_valid_file(validate_rn),
            self.is_there_spaces_in_the_end_of_id(),
        ])

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
                error_message, error_code = Errors.remove_field_from_dashboard(field)
                formatted_message = self.handle_error(error_message, error_code, file_path=self.file_path,
                                                      should_print=False)
                if formatted_message:
                    is_valid = False
                    error_msg += formatted_message
            # iterate over the widgets if exist
            if widgets:
                for widget in widgets:
                    if widget.get(field):
                        error_message, error_code = Errors.remove_field_from_widget(field, widget)
                        formatted_message = self.handle_error(error_message, error_code, file_path=self.file_path,
                                                              should_print=False)
                        if formatted_message:
                            is_valid = False
                            error_msg += formatted_message
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
                error_message, error_code = Errors.include_field_in_dashboard(field)
                formatted_message = self.handle_error(error_message, error_code, file_path=self.file_path,
                                                      should_print=False)
                if formatted_message:
                    is_valid = False
                    error_msg += formatted_message
            # iterate over the widgets if exist
            if widgets:
                for widget in widgets:
                    if not widget.get(field):
                        widget_name = widget.get("name")
                        error_message, error_code = Errors.include_field_in_widget(field, widget_name)
                        formatted_message = self.handle_error(error_message, error_code, file_path=self.file_path,
                                                              should_print=False)
                        if formatted_message:
                            is_valid = False
                            error_msg += formatted_message
        if error_msg:
            print_error(error_msg)
        return is_valid

    def is_there_spaces_in_the_end_of_id(self):
        """
        Returns:
            bool. Whether the dashboard's id has no spaces in the end
        """
        return super(DashboardValidator, self)._is_there_spaces_in_the_end_of_id('dashboard')
