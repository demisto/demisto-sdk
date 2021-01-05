import json
import re
from tempfile import NamedTemporaryFile
from typing import Callable, Union

import demisto_client
from demisto_sdk.commands.common.constants import (FEATURE_BRANCHES,
                                                   INCIDENT_TYPE,
                                                   OLDEST_SUPPORTED_VERSION)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.hook_validations.incident_type import \
    INVALID_PLAYBOOK_ID
from demisto_sdk.commands.common.tools import get_remote_file
from demisto_sdk.commands.format.format_constants import DEFAULT_VERSION
from packaging.version import Version
from wcmatch.pathlib import Path


class IncidentType(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, INCIDENT_TYPE)
        self.handle_error: Callable = BaseValidator().handle_error

    def upload(self, client: demisto_client):
        """
        Upload the incident type Container to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        if isinstance(self._as_dict, dict):
            incident_type_unified_data = [self._as_dict]
        else:
            incident_type_unified_data = self._as_dict

        with NamedTemporaryFile(suffix='.json') as incident_type_unified_file:
            incident_type_unified_file.write(bytes(json.dumps(incident_type_unified_data), 'utf-8'))
            incident_type_unified_file.seek(0)
            return client.import_incident_types_handler(file=incident_type_unified_file.name)

    def validate(self, check_bc, ignored_errors_list, print_as_warnings=False,
                 prev_ver='origin/master', branch_name=''):
        self.handle_error = BaseValidator(ignored_errors=ignored_errors_list, print_as_warnings=print_as_warnings). \
            handle_error

        old_file = get_remote_file(self.path, tag=prev_ver)
        if check_bc:
            return self.is_valid_file(old_file=old_file, prev_ver=prev_ver, branch_name=branch_name) and \
                self.is_backward_compatible(old_file=old_file)
        else:
            return self.is_valid_file(old_file=old_file, prev_ver=prev_ver, branch_name=branch_name)

    def is_backward_compatible(self, old_file):
        """Check whether the Incident Type is backward compatible or not
        """
        if not old_file:
            return True

        is_bc_broke = any(
            [
                self.is_changed_from_version(old_file)
            ]
        )

        return not is_bc_broke

    def is_valid_file(self, old_file, prev_ver, branch_name):
        """Check whether the Incident Type is valid or not
        """
        is_incident_type__valid = all([
            self.is_valid_fromversion(prev_ver=prev_ver, branch_name=branch_name),
            self.is_valid_version(),
            self.is_valid_autoextract()
        ])

        # check only on added files
        if not old_file:
            is_incident_type__valid = all([
                is_incident_type__valid,
                self.is_id_equals_name(),
                self.is_including_int_fields(),
                self.is_valid_playbook_id()
            ])

        return is_incident_type__valid

    def is_valid_version(self):
        # type: () -> bool
        """Base is_valid_version method for files that version is their root.

        Return:
            True if version is valid, else False
        """
        if self.get('version') != DEFAULT_VERSION:
            error_message, error_code = Errors.wrong_version(DEFAULT_VERSION)
            if self.handle_error(error_message, error_code, file_path=self.path,
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
            if self.handle_error(error_message, error_code, file_path=self.path,
                                 suggested_fix=Errors.suggest_fix(str(self.path))):
                return False

        return True

    def is_changed_from_version(self, old_file: dict) -> bool:
        """Check if fromversion has been changed.
       Returns:
           bool. Whether fromversion has been changed.
       """
        is_bc_broke = False

        old_from_version = old_file.get('fromVersion', None)
        if old_from_version:
            current_from_version = self.get('fromVersion', None)
            if old_from_version != current_from_version:
                error_message, error_code = Errors.from_version_modified_after_rename()
                if self.handle_error(error_message, error_code, file_path=self.path):
                    is_bc_broke = True
        return is_bc_broke

    def is_including_int_fields(self):
        # type: () -> bool
        """Check if including required fields, only from 5.0.0.
        Returns:
            bool. Whether the included fields have a positive integer value.
        """
        is_valid = True
        fields_to_include = ['hours', 'days', 'weeks', 'hoursR', 'daysR', 'weeksR']

        try:
            if self.from_version >= Version("5.0.0"):
                for field in fields_to_include:
                    int_field = self.get(field, -1)
                    if not isinstance(int_field, int) or int_field < 0:
                        error_message, error_code = Errors.incident_type_integer_field(field)
                        if self.handle_error(error_message, error_code, file_path=self.path):
                            is_valid = False

        except (AttributeError, ValueError):
            error_message, error_code = Errors.invalid_incident_field_or_type_from_version()
            if self.handle_error(error_message, error_code, file_path=self.path):
                is_valid = False

        return is_valid

    def is_valid_playbook_id(self):
        # type: () -> bool
        """Check if playbookId is valid
        Returns:
            bool. True if playbook ID is valid, False otherwise.
        """
        playbook_id = self.get('playbookId', '')
        if playbook_id and re.search(INVALID_PLAYBOOK_ID, playbook_id):
            error_message, error_code = Errors.incident_type_invalid_playbook_id_field()
            if self.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def is_valid_fromversion(self, prev_ver, branch_name):
        """Check if the file has a fromversion 5.0.0 or higher
            This is not checked if checking on or against a feature branch.
        """
        if not self.should_run_fromversion_validation(prev_ver, branch_name):
            return True

        if self.from_version < Version(OLDEST_SUPPORTED_VERSION):
            error_message, error_code = Errors.no_minimal_fromversion_in_file('fromVersion',
                                                                              OLDEST_SUPPORTED_VERSION)
            if self.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def should_run_fromversion_validation(self, prev_ver, branch_name):
        # skip check if the comparison is to a feature branch or if you are on the feature branch itself.
        # also skip if the file in question is reputations.json
        if any((feature_branch_name in prev_ver or feature_branch_name in branch_name)
               for feature_branch_name in FEATURE_BRANCHES) or str(self.path).endswith('reputations.json'):
            return False

        return True

    def is_valid_autoextract(self):
        """Check if extractSettings field is valid.

        Returns:
            bool. True if extractSettings is valid or empty, False otherwise
        """
        auto_extract_data = self.get('extractSettings', {})

        # no auto extraction set in incident type.
        if not auto_extract_data:
            return True

        auto_extract_fields = auto_extract_data.get('fieldCliNameToExtractSettings')
        auto_extract_mode = auto_extract_data.get('mode')

        is_valid = True

        if auto_extract_fields:
            invalid_incident_fields = []
            for incident_field, extracted_settings in auto_extract_fields.items():
                extracting_all = extracted_settings.get('isExtractingAllIndicatorTypes')
                extract_as_is = extracted_settings.get('extractAsIsIndicatorTypeId')
                extracted_indicator_types = extracted_settings.get('extractIndicatorTypesIDs')

                # General format check.
                if type(extracting_all) != bool or type(extract_as_is) != str or type(extracted_indicator_types) != list:
                    invalid_incident_fields.append(incident_field)

                # If trying to extract without regex make sure extract all is set to
                # False and the extracted indicators list is empty
                elif extract_as_is != "":
                    if extracting_all is True or len(extracted_indicator_types) > 0:
                        invalid_incident_fields.append(incident_field)

                # If trying to extract with regex make sure extract all is set to
                # False and the extract_as_is should be set to an empty string
                elif len(extracted_indicator_types) > 0:
                    if extracting_all is True or extract_as_is != "":
                        invalid_incident_fields.append(incident_field)

            if invalid_incident_fields:
                error_message, error_code = Errors.incident_type_auto_extract_fields_invalid(invalid_incident_fields)
                if self.handle_error(error_message, error_code, self.path):
                    is_valid = False

        if auto_extract_mode not in ['All', 'Specific']:
            error_message, error_code = Errors.incident_type_invalid_auto_extract_mode()
            if self.handle_error(error_message, error_code, self.path):
                is_valid = False

        return is_valid
