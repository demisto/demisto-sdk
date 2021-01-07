from typing import Union

import demisto_client
from demisto_sdk.commands.common.constants import (DASHBOARD, DEFAULT_VERSION,
                                                   FEATURE_BRANCHES,
                                                   OLDEST_SUPPORTED_VERSION)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import get_remote_file
from packaging.version import Version
from pipenv.patched.piptools import click
from wcmatch.pathlib import Path


class Dashboard(JSONContentObject):
    def __init__(self, path: Union[Path, str], base: BaseValidator = None):
        super().__init__(path, DASHBOARD)
        self.base = base if base else BaseValidator()

    def upload(self, client: demisto_client):
        """
        Upload the dashboard to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        return client.import_dashboard(file=self.path)

    def validate(self):
        old_file = get_remote_file(self.path, tag=self.base.prev_ver)
        return self.is_valid_dashboard(old_file)

    def is_valid_dashboard(self, old_file):
        # type: (dict) -> bool
        """Check whether the dashboard is valid or not.

        Returns:
            bool. Whether the dashboard is valid or not
        """
        is_dashboard_valid = all([
            self.is_valid_version(),
            self.is_valid_fromversion()
        ])

        # check only on added files
        if not old_file:
            is_dashboard_valid = all([
                is_dashboard_valid,
                self.is_id_equals_name(),
                self.is_including_fields(),
                self.contains_forbidden_fields()
            ])

        return is_dashboard_valid

    def is_valid_fromversion(self):
        """Check if the file has a fromversion 5.0.0 or higher
            This is not checked if checking on or against a feature branch.
        """
        if not self.should_run_fromversion_validation():
            return True

        if self.from_version < Version(OLDEST_SUPPORTED_VERSION):
            error_message, error_code = Errors.no_minimal_fromversion_in_file('fromVersion',
                                                                              OLDEST_SUPPORTED_VERSION)
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def should_run_fromversion_validation(self):
        # skip check if the comparison is to a feature branch or if you are on the feature branch itself.
        # also skip if the file in question is reputations.json
        if any((feature_branch_name in self.base.prev_ver or feature_branch_name in self.base.branch_name)
               for feature_branch_name in FEATURE_BRANCHES):
            return False

        return True

    def is_valid_version(self):
        # type: () -> bool
        """Base is_valid_version method for files that version is their root.

        Return:
            True if version is valid, else False
        """
        if self.get('version') != DEFAULT_VERSION:
            error_message, error_code = Errors.wrong_version(DEFAULT_VERSION)
            if self.base.handle_error(error_message, error_code, file_path=self.path,
                                      suggested_fix=Errors.suggest_fix(str(self.path))):
                return False
        return True

    def is_id_equals_name(self):
        """Validate that the id of the file equals to the name.

        Returns:
            bool. Whether the file's id is equal to to its name
        """

        file_id = self.get('id')
        name = self.get('name', '')
        if file_id != name:
            error_message, error_code = Errors.id_should_equal_name(name, file_id)
            if self.base.handle_error(error_message, error_code, file_path=self.path,
                                      suggested_fix=Errors.suggest_fix(self.path)):
                return False

        return True

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

        widgets = self.get_widgets_from_dashboard()

        for field in fields_to_exclude:
            if self.get(field) is not None:
                error_message, error_code = Errors.remove_field_from_dashboard(field)
                formatted_message = self.base.handle_error(error_message, error_code, file_path=self.path,
                                                           should_print=False)
                if formatted_message:
                    is_valid = False
                    error_msg += formatted_message
            # iterate over the widgets if exist
            if widgets:
                for widget in widgets:
                    if widget.get(field):
                        error_message, error_code = Errors.remove_field_from_widget(field, widget)
                        formatted_message = self.base.handle_error(error_message, error_code,
                                                                   file_path=self.path, should_print=False)
                        if formatted_message:
                            is_valid = False
                            error_msg += formatted_message
        if error_msg:
            click.secho(error_msg, fg='bright_red')
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

        widgets = self.get_widgets_from_dashboard()

        for field in fields_to_include:
            if not self.get(field):
                error_message, error_code = Errors.include_field_in_dashboard(field)
                formatted_message = self.base.handle_error(error_message, error_code, file_path=self.path,
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
                        formatted_message = self.base.handle_error(error_message, error_code,
                                                                   file_path=self.path, should_print=False)
                        if formatted_message:
                            is_valid = False
                            error_msg += formatted_message
        if error_msg:
            click.secho(error_msg, fg='bright_red')
        return is_valid

    def get_widgets_from_dashboard(self):
        # type: () -> list
        layout_of_dashboard: list = self.get('layout', [])
        widgets = []
        if layout_of_dashboard:
            widgets = [item.get('widget') for item in layout_of_dashboard]
        return widgets
