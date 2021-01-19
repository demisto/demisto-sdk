import pytest
from demisto_sdk.commands.common.hook_validations.classifier import \
    ClassifierValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from mock import patch


def mock_structure(file_path=None, current_file=None, old_file=None):
    with patch.object(StructureValidator, '__init__', lambda a, b: None):
        structure = StructureValidator(file_path)
        structure.is_valid = True
        structure.scheme_name = 'classifier'
        structure.file_path = file_path
        structure.current_file = current_file
        structure.old_file = old_file
        structure.prev_ver = 'master'
        structure.branch_name = ''
        return structure


class TestClassifierValidator:

    CLASSIFIER_WITH_VALID_INCIDENT_FIELD = {"mapping": {"0": {"internalMapping": {"Incident Field": "incident field"}}}}

    ID_SET_WITH_INCIDENT_FIELD = {"IncidentFields": [{"name": {"name": "Incident Field"}}],
                                  "IndicatorFields": [{"name": {"name": "Incident Field"}}]}

    ID_SET_WITHOUT_INCIDENT_FIELD = {"IncidentFields": [{"name": {"name": "name"}}],
                                     "IndicatorFields": [{"name": {"name": "name"}}]}

    IS_INCIDENT_FIELD_EXIST = [
        (CLASSIFIER_WITH_VALID_INCIDENT_FIELD, ID_SET_WITH_INCIDENT_FIELD, True, True),
        (CLASSIFIER_WITH_VALID_INCIDENT_FIELD, ID_SET_WITHOUT_INCIDENT_FIELD, True, False)
    ]

    @pytest.mark.parametrize("classifier_json, id_set_json, is_circle, expected_result", IS_INCIDENT_FIELD_EXIST)
    def test_is_incident_field_exist(self, repo, classifier_json, id_set_json, is_circle, expected_result):
        """
        Given
        - A mapper with incident fields
        - An id_set file.
        When
        - validating mapper
        Then
        - validating that incident fields exist in id_set.
        """
        repo.id_set.write_json(id_set_json)
        structure = mock_structure("", classifier_json)
        validator = ClassifierValidator(structure)
        assert validator.is_incident_field_exist(id_set_json, is_circle) == expected_result
