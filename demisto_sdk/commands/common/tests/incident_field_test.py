import pytest

from demisto_sdk.commands.common.hook_validations.incident_field import \
    IncidentFieldValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator

INCIDENT_GROUP_NUMBER = 0


class TestIncidentFieldValidator:
    @pytest.mark.parametrize('field_type', IncidentFieldValidator.FIELD_TYPES)
    def test_valid_incident_field_type(self, pack, field_type: str):
        """
        Given:
        - Incident field.

        When:
        - Validating a valid incident field.

        Then:
        - Ensure is valid file returns true.

        """
        incident_field = pack.create_incident_field('incident_1', {'type': field_type, 'cliName': 'testincident',
                                                                   'version': -1, 'fromVersion': '5.0.0',
                                                                   'content': True, 'group': INCIDENT_GROUP_NUMBER})
        structure = StructureValidator(incident_field.path)
        validator = IncidentFieldValidator(structure)
        assert validator.is_valid_file()

    def test_invalid_incident_field_type(self, pack):
        """
        Given:
        - Incident field.

        When:
        - Validating an invalid incident field.

        Then:
        - Ensure is valid file returns false.

        """
        incident_field = pack.create_incident_field('incident_1', {'type': 'lol-unknown', 'cliName': 'testincident',
                                                                   'version': -1, 'fromVersion': '5.0.0',
                                                                   'content': True, 'group': INCIDENT_GROUP_NUMBER})
        structure = StructureValidator(incident_field.path)
        validator = IncidentFieldValidator(structure)
        assert not validator.is_valid_file()
