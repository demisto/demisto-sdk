import pytest

from demisto_sdk.commands.validate.tests.test_tools import create_generic_field_object
from demisto_sdk.commands.validate.validators.GF_validators.GF101_generic_field_id_prefix_validate import (
    GenericFieldIdPrefixValidateValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msg",
    [
        (
            [
                create_generic_field_object(paths=["id"], values=["test"]),
                create_generic_field_object(paths=["id"], values=["generic_test"]),
            ],
            1,
            "ID test is not a valid generic field ID - it should start with the prefix generic_.",
        )
    ],
)
def test_GenericFieldIdPrefixValidateValidator_is_valid(
    content_items, expected_number_of_failures: int, expected_msg: str
):
    results = GenericFieldIdPrefixValidateValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(result.message == expected_msg for result in results)


def test_GenericFieldIdPrefixValidateValidator_fix():
    generic_field = create_generic_field_object(paths=["id"], values=["test"])
    
    result = GenericFieldIdPrefixValidateValidator().fix(generic_field)  # type:ignore
    assert result
    assert result.message == "Change the value of `id` field to generic_test."
