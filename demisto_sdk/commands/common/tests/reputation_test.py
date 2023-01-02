import pytest

from demisto_sdk.commands.common.hook_validations.reputation import ReputationValidator
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator

data_is_valid_version = [
    (-1, True),
    (0, False),
    (1, False),
]


@pytest.mark.parametrize("version, is_valid", data_is_valid_version)
def test_is_valid_version(version, is_valid):
    structure = StructureValidator("")
    structure.current_file = {"version": version}
    validator = ReputationValidator(structure)
    assert (
        validator.is_valid_version() == is_valid
    ), f"is_valid_version({version}) returns {not is_valid}."


data_is_valid_expiration = [(0, True), (500, True), (-1, False), ("not_valid", False)]


@pytest.mark.parametrize("expiration, is_valid", data_is_valid_expiration)
def test_is_valid_expiration(expiration, is_valid):
    structure = StructureValidator("")
    structure.current_file = {"fromVersion": "5.5.0", "expiration": expiration}
    validator = ReputationValidator(structure)
    assert validator.is_valid_expiration() == is_valid, (
        f"is_valid_expiration({expiration})" f" returns {not is_valid}."
    )


data_is_id_equals_details = [("CIDR", "CIDR", True), ("CIDR", "CIDR2", False)]


@pytest.mark.parametrize("id_, details, is_valid", data_is_id_equals_details)
def test_is_id_equals_details(id_, details, is_valid):
    structure = StructureValidator("")
    structure.current_file = {"id": id_, "details": details}
    validator = ReputationValidator(structure)
    assert validator.is_id_equals_details() == is_valid, (
        f"is_id_equals_details({id_}, {details})" f" returns {not is_valid}."
    )


data_is_valid_id = [
    ("CIDR", True),
    ("host_test", True),
    ("ipv4&ipv6", True),
    ("ipv4 ipv6", True),
    ("ipv4-ipv6", False),
    ("ipv4*ipv6", False),
]


@pytest.mark.parametrize("id_, is_valid", data_is_valid_id)
def test_is_valid_id_field(id_, is_valid):
    structure = StructureValidator("")
    structure.current_file = {"id": id_}
    validator = ReputationValidator(structure)
    assert validator.is_valid_indicator_type_id() == is_valid


data_is_empty_id_and_details = [
    ("CIDR", "CIDR", True),
    ("CIDR", "", False),
    ("", "CIDR", False),
]


@pytest.mark.parametrize("id_, details, is_valid", data_is_empty_id_and_details)
def test_is_id_and_details_empty(id_, details, is_valid):
    structure = StructureValidator("")
    structure.current_file = {"id": id_, "details": details}
    validator = ReputationValidator(structure)
    assert validator.is_required_fields_empty() == is_valid
