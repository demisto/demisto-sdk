import pytest

from demisto_sdk.commands.common.hook_validations.reputation import ReputationValidator
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator


data_is_valid_version = [
    (-1, True),
    (0, False),
    (1, False),
]


@pytest.mark.parametrize('version, is_valid', data_is_valid_version)
def test_is_valid_version(version, is_valid):
    structure = StructureValidator("")
    structure.current_file = {"version": version}
    validator = ReputationValidator(structure)
    assert validator.is_valid_version() == is_valid, f'is_valid_version({version}) returns {not is_valid}.'


data_is_valid_expiration = [
    (0, True),
    (500, True),
    (-1, False),
    ("not_valid", False)
]


@pytest.mark.parametrize('expiration, is_valid', data_is_valid_expiration)
def test_is_valid_expiration(expiration, is_valid):
    structure = StructureValidator("")
    structure.current_file = {"fromVersion": "5.5.0", "expiration": expiration}
    validator = ReputationValidator(structure)
    assert validator.is_valid_expiration() == is_valid, f'is_valid_expiration({expiration})' \
                                                        f' returns {not is_valid}.'


data_is_id_equals_name = [
    ("CIDR", "CIDR", True),
    ("CIDR", "CIDR2", False)
]


@pytest.mark.parametrize('id_, name, is_valid', data_is_id_equals_name)
def test_is_id_equals_name(id_, name, is_valid):
    structure = StructureValidator("")
    structure.current_file = {"id": id_, "name": name}
    validator = ReputationValidator(structure)
    assert validator.is_id_equals_name() == is_valid, f'is_id_equals_name({id_}, {name})' \
                                                      f' returns {not is_valid}.'
