import pytest

from demisto_sdk.commands.validate.validators.GF_validators.GF101_generic_field_id_prefix_validate import (
    GenericFieldIdPrefixValidateValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [],
            1,
            ["", ""]
        )
    ]
)
def test_GenericFieldIdPrefixValidateValidator_is_valid(
    content_items,
    expected_number_of_failures: int,
    expected_msgs: list[str]
):
    results = GenericFieldIdPrefixValidateValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        result == expected_msg
        for result, expected_msg in zip(results, expected_msgs)
    )


def test_GenericFieldIdPrefixValidateValidator_fix():
    ...