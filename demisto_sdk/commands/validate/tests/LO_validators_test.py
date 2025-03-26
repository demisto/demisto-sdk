from pathlib import Path
from typing import List, cast

import pytest

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.tests.test_tools import load_json
from demisto_sdk.commands.validate.tests.test_tools import create_layout_object
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator
from demisto_sdk.commands.validate.validators.LO_validators.LO100_validate_dynamic_section import (
    IsValidDynamicSectionValidator,
)
from demisto_sdk.commands.validate.validators.LO_validators.LO107_is_valid_type import (
    IsValidTypeValidator,
)
from TestSuite.repo import Repo


@pytest.mark.parametrize(
    "paths, values, expected_field_error_messages",
    [
        pytest.param(
            ["detailsV2.tabs[1].sections[0].type"],
            ["evidence"],
            ["evidence"],
            id="Single invalid type in a section of the second tab",
        )
    ],
)
def test_IsValidTypeValidator_obtain_invalid_content_items_failure(
    paths: List[str],
    values: List[str],
    expected_field_error_messages: List[str],
):
    """
    Given
        Case: a layout object with a single invalid type in a section of the second tab,
    When
        the IsValidTypeValidator's obtain_invalid_content_items method is called with the layout object.
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
        ]
    )
    values.extend(
        [
            "dynamic",
            "dynamic",
            "dynamic",
            "dynamic",
        ]
    )
    content_items = create_layout_object(paths=paths, values=values)
    results = IsValidTypeValidator().obtain_invalid_content_items([content_items])
    assert len(results) == 1  # one failure
    assert (
        results[0].message
        == f"The following invalid types were found in the layout: {', '.join(expected_field_error_messages)}. Those types are not supported in XSIAM, remove them or change the layout to be XSOAR only."
    )


def test_IsValidTypeValidator_obtain_invalid_content_items_success():
    """
    Given
        a layout object created by the create_layout_object function,
    When
        the IsValidTypeValidator's obtain_invalid_content_items method is called with the layout object,
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
        ],
        values=["dynamic", "dynamic", "dynamic", "dynamic"],
    )
    assert not IsValidTypeValidator().obtain_invalid_content_items(
        [valid_layout_object]
    )  # no failures


def test_IsValidTypeValidator_returns_no_failures_after_removal_of_MarketplaceV2():
    """
    Given
        a layout object that initially includes MarketplaceV2 in its marketplaces,
    When
        MarketplaceV2 in the marketplaces of the layout object,
    Then
        the IsValidTypeValidator's obtain_invalid_content_items method should initially return failures,
        but after the removal of MarketplaceV2, it should return no failures, indicating that the layout object is now valid.
    Note
        The create_layout_object() function is used to create a layout object.
        the layout object is invalid by default when the layout is for marketplaceV2
    """
    layout_object = create_layout_object()

    assert IsValidTypeValidator().obtain_invalid_content_items(
        [layout_object]
    ), "Expected initial validation to fail due to presence of MarketplaceV2"

    layout_object.marketplaces.remove(MarketplaceVersions.MarketplaceV2)

    assert not IsValidTypeValidator().obtain_invalid_content_items(
        [layout_object]
    ), "Expected validation to pass after removal of MarketplaceV2"


@pytest.fixture
def repo_for_test_layout(graph_repo):
    pack_1 = graph_repo.create_pack("Pack1")
    invalid_layout_object = f"{git_path()}/demisto_sdk/commands/validate/test_files/invalid_layoutscontainer.json"
    json_content = load_json(invalid_layout_object)
    pack_1.create_layout(name="layout", content=json_content)
    pack_1.create_script("TestScript")

    return graph_repo


def test_IsValidDynamicSectionValidator_script_not_found(
    repo_for_test_layout: Repo,
):
    """
    Given
        Invalid layout object with 2 invalid sections - one contains query with UUID and the other contains query with unknown script name.
    When
        the IsValidDynamicSectionValidator's obtain_invalid_content_items method is called with the layout object,
    Then
        the obtain_invalid_content_items method should return  2 failures, one for invalid query with UUID and the other for unknown script name.
    """
    graph_interface = repo_for_test_layout.create_graph()
    BaseValidator.graph_interface = graph_interface
    layout_object = cast(
        Layout,
        BaseContent.from_path(Path(repo_for_test_layout.packs[0].layouts[0].path)),
    )
    results = IsValidDynamicSectionValidator().obtain_invalid_content_items(
        content_items=[layout_object]
    )
    assert (
        results[0].message
        == "The tab XDR Device Control Violations contains the following script that not exists in the repo: TestScript2."
    )
    results[
        1
    ].message == "The tab XDR Device Control Violations contains UUID value: 612ad420-04a9-11eb-ba3b-5h42d710bdf4 in the query field, please change it to valid script name."
