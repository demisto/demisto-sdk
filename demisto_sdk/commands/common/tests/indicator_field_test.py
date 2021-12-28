import pytest

from demisto_sdk.commands.common.hook_validations.indicator_field import \
    IndicatorFieldValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator

INDICATOR_GROUP_NUMBER = 2


class TestIndicatorFieldValidator:
    @pytest.mark.parametrize('field_type', IndicatorFieldValidator.FIELD_TYPES)
    def test_valid_indicator_field_type(self, pack, field_type: str):
        """
        Given:
        - Indicator field.

        When:
        - Validating a valid indicator field.

        Then:
        - Ensure is valid file returns true.

        """
        indicator_field = pack.create_indicator_field('incident_1', {'type': field_type, 'cliName': 'testindicator',
                                                                     'version': -1, 'fromVersion': '5.5.0',
                                                                     'content': True, 'group': INDICATOR_GROUP_NUMBER})
        structure = StructureValidator(indicator_field.path)
        validator = IndicatorFieldValidator(structure)
        assert validator.is_valid_file()

    def test_invalid_incident_field_type(self, pack):
        """
        Given:
        - Indicator field.

        When:
        - Validating an invalid indicator field.

        Then:
        - Ensure is valid file returns false.

        """
        indicator_field = pack.create_indicator_field('incident_1', {'type': 'lol-unknown', 'cliName': 'testindicator',
                                                                     'version': -1, 'fromVersion': '5.0.0',
                                                                     'content': True, 'group': INDICATOR_GROUP_NUMBER})
        structure = StructureValidator(indicator_field.path)
        validator = IndicatorFieldValidator(structure)
        assert not validator.is_valid_file()

    def test_invalid_grid_from_version(self, pack):
        """
        Given:
        - Indicator field.

        When:
        - Validating an invalid indicator field, with from version below 5.5.0 and type of grid.

        Then:
        - Ensure is valid file returns false.

        """
        indicator_field = pack.create_indicator_field('incident_1', {'type': 'grid', 'cliName': 'testindicator',
                                                                     'version': -1, 'fromVersion': '5.0.0',
                                                                     'content': True, 'group': INDICATOR_GROUP_NUMBER})
        structure = StructureValidator(indicator_field.path)
        validator = IndicatorFieldValidator(structure)
        assert not validator.is_valid_file()

    TYPES_FROM_VERSION = [
        ('grid', '5.5.0', True),
        ('grid', '5.0.0', False),
        ('number', '5.0.0', True),
        ('html', '6.1.0', True),
        ('html', '6.0.0', False),
    ]

    @pytest.mark.parametrize('field_type, from_version, expected', TYPES_FROM_VERSION)
    def test_is_valid_indicator_type_from_version(self, pack, field_type, from_version, expected):
        """
        Given
        - An indicator field, with its type

        When
        - Running valid_indicator_type_from_version on it.

        Then
        - Ensure if minimal version is needed, and the fromVersion of the indicator field does not satisfy the
          minimal condition, false is returned. Otherwise ensure true is returned.
        """
        indicator_field = pack.create_indicator_field('incident_1', {'type': field_type, 'cliName': 'testindicator',
                                                                     'version': -1, 'fromVersion': from_version,
                                                                     'content': True, 'group': INDICATOR_GROUP_NUMBER})
        structure = StructureValidator(indicator_field.path)
        validator = IndicatorFieldValidator(structure)
        assert validator.is_valid_indicator_type_from_version() == expected

