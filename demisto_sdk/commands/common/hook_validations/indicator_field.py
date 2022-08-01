"""
This module is designed to validate the correctness of incident field entities in content.
"""
from distutils.version import LooseVersion
from typing import Optional

from demisto_sdk.commands.common.constants import \
    INDICATOR_FIELD_TYPE_TO_MIN_VERSION
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
            self.is_valid_indicator_type_from_version(),
        ]
        return all(answers)

    def is_valid_indicator_type_from_version(self) -> bool:
        """
        Validate that a indicator field with type grid is from version >= 5.5.0.
        Returns:
            (bool): True if field type is not grid, or is grid type and its from version is above 5.5.0.
                    False otherwise.
        """
        indicator_field_type: Optional[str] = self.current_file.get('type')
        if indicator_field_type not in INDICATOR_FIELD_TYPE_TO_MIN_VERSION:
            return True
        min_version: LooseVersion = INDICATOR_FIELD_TYPE_TO_MIN_VERSION[indicator_field_type]
        return self.is_valid_from_version_field(min_version, f'Indicator field of type {indicator_field_type}.')
