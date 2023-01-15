from typing import Optional
from unittest.mock import patch

import pytest

from demisto_sdk.commands.common.hook_validations.dashboard import DashboardValidator
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator


def mock_structure(
    file_path: Optional[str] = None,
    current_file: Optional[dict] = None,
    old_file: Optional[dict] = None,
) -> StructureValidator:
    with patch.object(StructureValidator, "__init__", lambda a, b: None):
        structure = StructureValidator(file_path)
        structure.is_valid = True
        structure.scheme_name = "dashboard"
        structure.file_path = file_path
        structure.current_file = current_file
        structure.old_file = old_file
        structure.prev_ver = "master"
        structure.branch_name = ""
        structure.specific_validations = None
        return structure


data_is_valid_version = [
    (-1, True),
    (0, False),
    (1, False),
]


@pytest.mark.parametrize("version, is_valid", data_is_valid_version)
def test_is_valid_version(version, is_valid):
    structure = StructureValidator("")
    structure.current_file = {"version": version}
    validator = DashboardValidator(structure)
    assert (
        validator.is_valid_version() == is_valid
    ), f"is_valid_version({version}) returns {not is_valid}."


data_is_id_equal_name = [
    ("aa", "aa", True),
    ("aa", "ab", False),
    ("my-home-dashboard", "My Dashboard", False),
]


@pytest.mark.parametrize("id_, name, is_valid", data_is_id_equal_name)
def test_is_id_equal_name(id_, name, is_valid):
    structure = StructureValidator("")
    structure.current_file = {"id": id_, "name": name}
    validator = DashboardValidator(structure)
    assert (
        validator.is_id_equals_name() == is_valid
    ), f"is_id_equal_name returns {not is_valid}."


data_contains_forbidden_fields = [
    ({"system": False}, False),
    ({"isCommon": False}, False),
    ({"shared": False}, False),
    ({"owner": "Admin"}, False),
    ({"layout": [{"widget": {"owner": "Admin"}}]}, False),
    ({"layout": [{"widget": {"shared": "False"}}]}, False),
    ({"layout": [{"widget": {"shared4": "False"}}]}, True),
]


@pytest.mark.parametrize("current_file, is_valid", data_contains_forbidden_fields)
def test_contains_forbidden_fields(current_file, is_valid):
    structure = mock_structure("", current_file)
    validator = DashboardValidator(structure)
    assert (
        validator.contains_forbidden_fields() == is_valid
    ), f"is_excluding_fields returns {not is_valid}."


data_is_including_fields = [
    ({"fromDate": "1", "toDate": "2", "fromDateLicense": "3"}, True),
    ({"fromDate": "1", "toDate": "2"}, False),
    (
        {
            "fromDate": "1",
            "toDate": "2",
            "fromDateLicense": "3",
            "layout": [
                {"widget": {"fromDate": "1", "toDate": "2", "fromDateLicense": "3"}}
            ],
        },
        True,
    ),
    (
        {
            "fromDate": "1",
            "toDate": "2",
            "fromDateLicense": "3",
            "layout": [
                {"widget": {"name": "bla", "fromDate": "1", "fromDateLicense": "3"}}
            ],
        },
        False,
    ),
]


@pytest.mark.parametrize("current_file, is_valid", data_is_including_fields)
def test_is_including_fields(current_file, is_valid):
    structure = mock_structure("", current_file)
    validator = DashboardValidator(structure)
    assert (
        validator.is_including_fields() == is_valid
    ), f"is_including_fields returns {not is_valid}."
