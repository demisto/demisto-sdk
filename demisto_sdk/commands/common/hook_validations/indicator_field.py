"""
This module is designed to validate the correctness of incident field entities in content.
"""
from distutils.version import LooseVersion

from demisto_sdk.commands.common.constants import \
    DEFAULT_CONTENT_ITEM_FROM_VERSION
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.field_base_validator import \
    FieldBaseValidator


class IndicatorFieldValidator(FieldBaseValidator):
    """IncidentFieldValidator is designed to validate the correctness of the file structure we enter to content repo.
    And also try to catch possible Backward compatibility breaks due to the performed changes.
    """
    FIELD_TYPES = {'grid', 'longText', 'markdown', 'url', 'role', 'tagsSelect', 'date', 'multiSelect', 'singleSelect',
                   'boolean', 'html', 'number', 'shortText', 'user'}
    PROHIBITED_CLI_NAMES = {'id', 'modified', 'type', 'rawname', 'name', 'createdtime', 'name', 'createdtime',
                            'investigationids', 'investigationscount', 'isioc', 'score', 'lastseen',
                            'lastreputationRun', 'firstseen', 'calculatedtime', 'source', 'rawsource', 'manualscore',
                            'setby', 'manualsetTime', 'comment', 'modifiedtime', 'sourceinstances', 'sourcebrands',
                            'context', 'expiration', 'expirationstatus', 'manuallyeditedfields', 'moduletofeedmap',
                            'isshared'}

    def __init__(self, structure_validator, ignored_errors=False,
                 print_as_warnings=False, json_file_path=None, **kwargs):
        super().__init__(structure_validator, self.FIELD_TYPES, self.PROHIBITED_CLI_NAMES, ignored_errors,
                         print_as_warnings, json_file_path=json_file_path, **kwargs)

    def is_valid_file(self, validate_rn=True, is_new_file=False, use_git=False, is_added_file=False) -> bool:
        """
        Check whether the indicator field is valid.
        Args:
            validate_rn (bool): Whether to validate release notes (changelog) or not.
            is_new_file (bool): Whether file is a new file.
            use_git (bool): Whether to use git.
            is_added_file (bool): Whether file is an added file.

        Returns:
            bool: True if indicator field is valid, False otherwise.
        """
        answers = [
            super().is_valid_file(validate_rn),
            self.is_valid_indicator_grid_from_version(),
        ]
        return all(answers)

    def is_valid_indicator_grid_from_version(self) -> bool:
        """
        Validate that a indicator field with type grid is from version >= 5.5.0.
        Returns:
            (bool): True if field type is not grid, or is grid type and its from version is above 5.5.0.
                    False otherwise.
        """

        if self.current_file.get('type') != 'grid':
            return True
        current_version = LooseVersion(self.current_file.get('fromVersion', DEFAULT_CONTENT_ITEM_FROM_VERSION))
        if current_version < LooseVersion('5.5.0'):
            error_message, error_code = Errors.indicator_field_type_grid_minimal_version(current_version)
            if self.handle_error(error_message, error_code, file_path=self.file_path,
                                 warning=self.structure_validator.quite_bc):
                return False
        return True
