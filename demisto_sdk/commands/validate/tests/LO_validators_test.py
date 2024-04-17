from typing import List

import pytest

from demisto_sdk.commands.validate.tests.test_tools import create_layout_object
from demisto_sdk.commands.validate.validators.LO_validators.LO107_is_valid_type import (
    ContentTypes as ContentTypes107,
)
from demisto_sdk.commands.validate.validators.LO_validators.LO107_is_valid_type import (
    IsValidTypeValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_field_error_messages",
    [
        pytest.param(
            create_layout_object(paths=["detailsV2.tabs[0].type"], values=["canvas"]),
            ["canvas"],
            id="Case1: Single invalid type in first tab",
        ),
        pytest.param(
            create_layout_object(
                paths=["detailsV2.tabs[1].sections[0].type"], values=["evidence"]
            ),
            ["evidence"],
            id="Case2: Single invalid type in a section of the second tab",
        ),
        pytest.param(
            create_layout_object(
                paths=["detailsV2.tabs[1].sections[0].type", "detailsV2.tabs[0].type"],
                values=["evidence", "canvas"],
            ),
            ["canvas", "evidence"],
            id="Case3: Multiple invalid types in different tabs",
        ),
    ],
)
def test_IIsValidTypeValidator_is_valid_failure(
    content_items: ContentTypes107,
    expected_field_error_messages: List[str],
):
    """
    Given
        Case1: a layout object with a single invalid type in the first tab,
        Case2: a layout object with a single invalid type in a section of the second tab,
        Case3: a layout object with multiple invalid types in different tabs,
    When
        the IsValidTypeValidator's is_valid method is called with the layout object,
    Then
        it should return a list of results with one failure message that matches the expected error message.
    """
    results = IsValidTypeValidator().is_valid([content_items])
    assert len(results) == 1  # one failure
    assert (
        results[0].message
        == f"The following invalid types were found in the layout: {', '.join(expected_field_error_messages)}. Those types are not supported in XSIAM, remove them or change the layout to be XSOAR only."
    )


def test_IsContentItemNameContainTrailingSpacesValidator_is_valid_success():
    """
    Given a layout object created by the create_layout_object function,
    When the IsValidTypeValidator's is_valid method is called with the layout object,
    Then it should return no failures, indicating that the layout object is valid.
    """
    assert not IsValidTypeValidator().is_valid(
        [create_layout_object()]  # type: ignore[reportArgumentType]
    )  # no failures
