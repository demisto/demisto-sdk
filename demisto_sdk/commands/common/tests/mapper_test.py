from unittest.mock import patch

import pytest

from demisto_sdk.commands.common.hook_validations.mapper import MapperValidator
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator


def mock_structure(file_path=None, current_file=None, old_file=None):
    with patch.object(StructureValidator, "__init__", lambda a, b: None):
        structure = StructureValidator(file_path)
        structure.is_valid = True
        structure.scheme_name = "mapper"
        structure.file_path = file_path
        structure.current_file = current_file
        structure.old_file = old_file
        structure.prev_ver = "master"
        structure.branch_name = ""
        structure.specific_validations = None
        return structure


class TestMapperValidator:

    INCOMING_MAPPER = {
        "mapping": {
            "0": {"internalMapping": {"Incident Field": {"simple": "Incident Field"}}}
        },
        "type": "mapping-incoming",
    }

    OUTGOING_MAPPER = {
        "mapping": {
            "0": {"internalMapping": {"Incident Field": {"simple": "Incident Field"}}}
        },
        "type": "mapping-outgoing",
    }

    ID_SET_WITH_INCIDENT_FIELD = {
        "IncidentFields": [{"name": {"name": "Incident Field"}}],
        "IndicatorFields": [{"name": {"name": "Incident Field"}}],
    }

    ID_SET_WITHOUT_INCIDENT_FIELD = {
        "IncidentFields": [{"name": {"name": "name"}}],
        "IndicatorFields": [{"name": {"name": "name"}}],
    }

    IS_INCIDENT_FIELD_EXIST = [
        (INCOMING_MAPPER, ID_SET_WITH_INCIDENT_FIELD, True, True),
        (INCOMING_MAPPER, ID_SET_WITHOUT_INCIDENT_FIELD, True, False),
        (OUTGOING_MAPPER, ID_SET_WITH_INCIDENT_FIELD, True, True),
        (OUTGOING_MAPPER, ID_SET_WITHOUT_INCIDENT_FIELD, True, False),
    ]

    @pytest.mark.parametrize(
        "mapper_json, id_set_json, is_circle, expected_result", IS_INCIDENT_FIELD_EXIST
    )
    def test_is_incident_field_exist(
        self, repo, mapper_json, id_set_json, is_circle, expected_result
    ):
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
        structure = mock_structure("", mapper_json)
        validator = MapperValidator(structure)
        assert (
            validator.is_incident_field_exist(id_set_json, is_circle) == expected_result
        )

    IS_MATCHING_NAME_ID_INPUT = [
        ({"id": "name", "name": "name"}, True),
        ({"id": "id_field", "name": "name_field"}, False),
    ]

    @pytest.mark.parametrize("mapper, result", IS_MATCHING_NAME_ID_INPUT)
    def test_is_name_id_equal(self, repo, mapper, result):
        """
        Given
        - A mapper with name and id
        When
        - validating mapper
        Then
        - validating that the mapper name and id are equal.
        """

        structure = mock_structure("", mapper)
        validator = MapperValidator(structure)

        assert validator.is_id_equals_name() == result
