from unittest.mock import patch

import pytest

from demisto_sdk.commands.common.hook_validations.classifier import ClassifierValidator
from demisto_sdk.commands.common.hook_validations.mapper import MapperValidator
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator


def mock_structure(file_path=None, current_file=None, old_file=None):
    with patch.object(StructureValidator, "__init__", lambda a, b: None):
        structure = StructureValidator(file_path)
        structure.is_valid = True
        structure.scheme_name = "classifier"
        structure.file_path = file_path
        structure.current_file = current_file
        structure.old_file = old_file
        structure.prev_ver = "master"
        structure.branch_name = ""
        structure.quiet_bc = False
        structure.specific_validations = None
        return structure


class TestClassifierValidator:
    CLASSIFIER_WITH_VALID_INCIDENT_FIELD = {
        "mapping": {"0": {"internalMapping": {"Incident Field": "incident field"}}}
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
        (CLASSIFIER_WITH_VALID_INCIDENT_FIELD, ID_SET_WITH_INCIDENT_FIELD, True, True),
        (
            CLASSIFIER_WITH_VALID_INCIDENT_FIELD,
            ID_SET_WITHOUT_INCIDENT_FIELD,
            True,
            False,
        ),
    ]

    @pytest.mark.parametrize(
        "classifier_json, id_set_json, is_circle, expected_result",
        IS_INCIDENT_FIELD_EXIST,
    )
    def test_is_incident_field_exist(
        self, repo, classifier_json, id_set_json, is_circle, expected_result
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
        structure = mock_structure("", classifier_json)
        validator = ClassifierValidator(structure)
        assert (
            validator.is_incident_field_exist(id_set_json, is_circle) == expected_result
        )

    OLD_MAPPER = {
        "mapping": {
            "1": {"internalMapping": {"field1": {"data1"}, "field2": {"data2"}}},
            "2": {"internalMapping": {"field1": {"data1"}, "field2": {"data2"}}},
        }
    }
    NEW_MAPPER_WITH_DELETED_TYPES = {
        "mapping": {
            "1": {"internalMapping": {"field1": {"data1"}, "field2": {"data2"}}}
        }
    }
    NEW_MAPPER_WITH_DELETED_FIELDS = {
        "mapping": {
            "1": {"internalMapping": {"field1": {"data1"}, "field2": {"data2"}}},
            "2": {"internalMapping": {"field1": {"data1"}}},
        }
    }
    NEW_VALID_MAPPER = {
        "mapping": {
            "1": {"internalMapping": {"field1": {"data1"}, "field2": {"data2"}}},
            "2": {"internalMapping": {"field1": {"new_data1"}, "field2": {"data2"}}},
        }
    }

    IS_CHANGED_INCIDENTS_FIELDS_INPUT = [
        (OLD_MAPPER, NEW_MAPPER_WITH_DELETED_FIELDS, True),
        (OLD_MAPPER, NEW_MAPPER_WITH_DELETED_TYPES, True),
        (OLD_MAPPER, NEW_VALID_MAPPER, False),
    ]

    @pytest.mark.parametrize(
        "old_file, current_file, answer", IS_CHANGED_INCIDENTS_FIELDS_INPUT
    )
    def test_is_changed_removed_yml_fields(self, old_file, current_file, answer):
        """
        Given
        - A mapper with incident fields
        When
        - running is_changed_incidents_fields
        Then
        - checks that incident fields or incidents types were not removed.
        """
        structure = mock_structure("", current_file, old_file)
        validator = MapperValidator(structure)

        assert validator.is_field_mapping_removed() == answer
        assert validator.is_valid != answer
        structure.quiet_bc = True
        assert validator.is_field_mapping_removed() is False

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
        validator = ClassifierValidator(structure)

        assert validator.is_id_equals_name() == result
