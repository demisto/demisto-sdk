from typing import List

import pytest

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.validate.tests.test_tools import create_layout_object
from demisto_sdk.commands.validate.validators.LO_validators.LO107_is_valid_type import (
    IsValidTypeValidator,
)


@pytest.mark.parametrize(
    "paths, values, expected_field_error_messages",
    [
        pytest.param(
            ["detailsV2.tabs[0].type"],
            ["canvas"],
            ["canvas"],
            id="Case1: Single invalid type in first tab",
        ),
        pytest.param(
            ["detailsV2.tabs[1].sections[0].type"],
            ["evidence"],
            ["evidence"],
            id="Case2: Single invalid type in a section of the second tab",
        ),
        pytest.param(
            ["detailsV2.tabs[1].sections[0].type", "detailsV2.tabs[0].type"],
            ["evidence", "canvas"],
            ["canvas", "evidence"],
            id="Case3: Multiple invalid types in different tabs",
        ),
    ],
)
def test_IsValidTypeValidator_is_valid_failure(
    paths: List[str],
    values: List[str],
    expected_field_error_messages: List[str],
):
    """
    Given
        Case1: a layout object with a single invalid type in the first tab,
        Case2: a layout object with a single invalid type in a section of the second tab,
        Case3: a layout object with multiple invalid types in different tabs,
    When
        the IsValidTypeValidator's is_valid method is called with the layout object.
    Then
        it should return a list of results with one failure message that matches the expected error message.
    Note
        The create_layout_object() function returns an invalid layout object by default when the layout is for marketplaceV2.
        Therefore, we manually change the values to only check the values that came from the parametrize.
    """
    # Extend the paths and values to make the layout object valid for some values
    paths.extend(
        [
            "detailsV2.tabs[1].sections[2].type",
            "detailsV2.tabs[1].sections[3].type",
            "detailsV2.tabs[4].type",
            "detailsV2.tabs[5].type",
            "detailsV2.tabs[6].type",
        ]
    )
    values.extend(
        [
            "dynamic",
            "dynamic",
            "dynamic",
            "dynamic",
            "dynamic",
        ]
    )
    content_items = create_layout_object(paths=paths, values=values)
    results = IsValidTypeValidator().is_valid([content_items])  # type: ignore[reportArgumentType]
    assert len(results) == 1  # one failure
    assert (
        results[0].message
        == f"The following invalid types were found in the layout: {', '.join(expected_field_error_messages)}. Those types are not supported in XSIAM, remove them or change the layout to be XSOAR only."
    )


def test_IsValidTypeValidator_is_valid_success():
    """
    Given
        a layout object created by the create_layout_object function,
    When
        the IsValidTypeValidator's is_valid method is called with the layout object,
    Then
        it should return no failures, indicating that the layout object is valid.
    Note
        The create_layout_object() function is used to create a layout object.
        the layout object is invalid by default when the layout is for marketplaceV2
    """
    valid_layout_object = create_layout_object(  # Create a valid layout object
        paths=[
            "detailsV2.tabs[1].sections[2].type",
            "detailsV2.tabs[1].sections[3].type",
            "detailsV2.tabs[4].type",
            "detailsV2.tabs[5].type",
            "detailsV2.tabs[6].type",
        ],
        values=["dynamic", "dynamic", "dynamic", "dynamic", "dynamic"],
    )
    assert not IsValidTypeValidator().is_valid(
        [valid_layout_object]  # type: ignore[reportArgumentType]
    )  # no failures


def test_IsValidTypeValidator_returns_no_failures_after_removal_of_MarketplaceV2():
    """
    Given
        a layout object that initially includes MarketplaceV2 in its marketplaces,
    When
        MarketplaceV2 in the marketplaces of the layout object,
    Then
        the IsValidTypeValidator's is_valid method should initially return failures,
        but after the removal of MarketplaceV2, it should return no failures, indicating that the layout object is now valid.
    Note
        The create_layout_object() function is used to create a layout object.
        the layout object is invalid by default when the layout is for marketplaceV2
    """
    layout_object = create_layout_object()

    assert IsValidTypeValidator().is_valid(
        [layout_object]  # type: ignore[reportArgumentType]
    ), "Expected initial validation to fail due to presence of MarketplaceV2"

    layout_object.marketplaces.remove(MarketplaceVersions.MarketplaceV2)  # type: ignore

    assert not IsValidTypeValidator().is_valid(
        [layout_object]  # type: ignore[reportArgumentType]
    ), "Expected validation to pass after removal of MarketplaceV2"
