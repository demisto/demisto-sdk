from unittest.mock import patch

import pytest

from demisto_sdk.commands.common.hook_validations.layout import (
    LayoutsContainerValidator,
    LayoutValidator,
)
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator


def mock_structure(file_path=None, current_file=None, old_file=None):
    with patch.object(StructureValidator, "__init__", lambda a, b: None):
        structure = StructureValidator(file_path)
        structure.is_valid = True
        structure.scheme_name = "layout"
        structure.file_path = file_path
        structure.current_file = current_file
        structure.old_file = old_file
        structure.prev_ver = "master"
        structure.branch_name = ""
        structure.specific_validations = None
        return structure


class TestLayoutValidator:
    LAYOUT_WITH_VALID_INCIDENT_FIELD = {
        "layout": {"tabs": [{"sections": [{"items": [{"fieldId": "Incident Field"}]}]}]}
    }

    LAYOUT_CONTAINER_WITH_VALID_INCIDENT_FIELD = {
        "detailsV2": {
            "tabs": [{"sections": [{"items": [{"fieldId": "Incident Field"}]}]}]
        }
    }

    LAYOUT_CONTAINER_WITH_INVALID_TYPES = {
        "detailsV2": {
            "tabs": [
                {"sections": [{"type": "evidence"}]},
                {"id": "canvas", "name": "Canvas", "type": "canvas"},
            ]
        },
        "marketplaces": ["marketplacev2"],
    }

    LAYOUT_CONTAINER_WITHOUT_INVALID_TYPES = {
        "detailsV2": {
            "tabs": [{"sections": [{"items": [{"fieldId": "Incident Field"}]}]}]
        },
        "marketplaces": ["marketplacev2"],
    }

    ID_SET_WITH_INCIDENT_FIELD = {
        "IncidentFields": [{"Incident Field": {"name": "Incident Field"}}],
        "IndicatorFields": [{"Incident Field": {"name": "Incident Field"}}],
    }

    ID_SET_WITHOUT_INCIDENT_FIELD = {
        "IncidentFields": [{"fields": {"name": "name"}}],
        "IndicatorFields": [{"fields": {"name": "name"}}],
    }

    IS_INCIDENT_FIELD_EXIST = [
        (LAYOUT_WITH_VALID_INCIDENT_FIELD, ID_SET_WITH_INCIDENT_FIELD, True, True),
        (LAYOUT_WITH_VALID_INCIDENT_FIELD, ID_SET_WITHOUT_INCIDENT_FIELD, True, False),
    ]

    @pytest.mark.parametrize(
        "layout_json, id_set_json, is_circle, expected_result", IS_INCIDENT_FIELD_EXIST
    )
    def test_layout_is_incident_field_exist_in_content(
        self, repo, layout_json, id_set_json, is_circle, expected_result
    ):
        """
        Given
        - A layout with incident fields
        - An id_set file.
        When
        - validating layout
        Then
        - validating that incident fields exist in id_set.
        """
        repo.id_set.write_json(id_set_json)
        structure = mock_structure("", layout_json)
        validator = LayoutValidator(structure)
        assert (
            validator.is_incident_field_exist(id_set_json, is_circle) == expected_result
        )

    IS_INCIDENT_FIELD_EXIST = [
        (
            LAYOUT_CONTAINER_WITH_VALID_INCIDENT_FIELD,
            ID_SET_WITH_INCIDENT_FIELD,
            True,
            True,
        ),
        (
            LAYOUT_CONTAINER_WITH_VALID_INCIDENT_FIELD,
            ID_SET_WITHOUT_INCIDENT_FIELD,
            True,
            False,
        ),
    ]

    @pytest.mark.parametrize(
        "layout_json, id_set_json, is_circle, expected_result", IS_INCIDENT_FIELD_EXIST
    )
    def test_layout_container_is_incident_field_exist_in_content(
        self, repo, layout_json, id_set_json, is_circle, expected_result
    ):
        """
        Given
        - A layout container with incident fields
        - An id_set file.
        When
        - validating layout container
        Then
        - validating that incident fields exist in id_set.
        """
        repo.id_set.write_json(id_set_json)
        structure = mock_structure("", layout_json)
        validator = LayoutsContainerValidator(structure)
        assert (
            validator.is_incident_field_exist(id_set_json, is_circle) == expected_result
        )

    IS_VALID_MPV2 = [
        (LAYOUT_CONTAINER_WITH_INVALID_TYPES, False),
        (LAYOUT_CONTAINER_WITHOUT_INVALID_TYPES, True),
    ]

    @pytest.mark.parametrize("layout_json, expected_result", IS_VALID_MPV2)
    def test_is_valid_mpv2_layout(self, repo, layout_json, expected_result):
        """
        Given: layout with section and fields.

        When: adding layout container to the repo.

        Then: Validate that the layout contain only valid types, if its being uploaded to mpv2.

        """
        structure = mock_structure("", layout_json)
        validator = LayoutsContainerValidator(structure)
        assert validator.is_valid_mpv2_layout() == expected_result

    IS_MATCHING_NAME_ID_INPUT = [
        ({"id": "name", "name": "name"}, True),
        ({"id": "id_field", "name": "name_field"}, False),
    ]

    @pytest.mark.parametrize("layout_container, result", IS_MATCHING_NAME_ID_INPUT)
    def test_is_name_id_equal(self, repo, layout_container, result):
        """
        Given
        - A layout container with name and id
        When
        - validating layout container
        Then
        - validating that layout_container name and id are equal.
        """

        structure = mock_structure("", layout_container)
        validator = LayoutsContainerValidator(structure)

        assert validator.is_id_equals_name() == result

    @staticmethod
    def test_is_valid_layout_container():
        layout = {
            "version": -1,
            "name": "test layout container",
        }
        structure = mock_structure("layout.json", layout)
        validator = LayoutsContainerValidator(structure)
        assert not validator.is_valid_layout(validate_rn=False)
