from unittest.mock import patch

import pytest

from demisto_sdk.commands.content_graph.common import (
    ContentType,
    MarketplaceVersions,
    replace_incorrect_marketplace,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
    to_node_pattern,
)


def test_content_type_does_not_contain_colon():
    """
    A colon is a special character in neo4j Cypher indicates when the label starts in the query, e.g.:
    `MATCH (n:Integration) return n`
    We want to make sure there are no colons in all content type values.
    """

    for content_type in ContentType:
        assert ":" not in content_type.value


def test_to_neo4j_pattern():
    properties = {
        "name": "test",
        "object_ids": ["1", "2"],
        "marketplaces": "xsoar",
        "version": 1,
        "version_float": 1.0,
    }
    pattern = to_node_pattern(
        properties=properties,
        content_type=ContentType.INTEGRATION,
        list_properties=["marketplaces"],
    )
    assert (
        pattern
        == "(node:Integration{name: \"test\", version: 1, version_float: 1.0} WHERE node.object_ids IN ['1', '2'] AND 'xsoar' IN node.marketplaces)"
    )


@pytest.mark.parametrize(
    "data, marketplace, expected",
    [
        (
            "This is a Cortex XSOAR v1 example.",
            MarketplaceVersions.MarketplaceV2,
            "This is a Cortex example.",
        ),
        (
            "This is a Cortex XSOAR example.",
            MarketplaceVersions.MarketplaceV2,
            "This is a Cortex example.",
        ),
        (
            "This is a Cortex XSOAR v1 example.",
            MarketplaceVersions.XSOAR,
            "This is a Cortex XSOAR v1 example.",
        ),
        (
            {
                "description": "This is a Cortex XSOAR v1 example.",
                "details": "Cortex XSOAR should be replaced.",
            },
            MarketplaceVersions.MarketplaceV2,
            {
                "description": "This is a Cortex example.",
                "details": "Cortex should be replaced.",
            },
        ),
        (
            ["This is a Cortex XSOAR v1 example.", "Cortex XSOAR should be replaced."],
            MarketplaceVersions.MarketplaceV2,
            ["This is a Cortex example.", "Cortex should be replaced."],
        ),
    ],
)
def test_replace_incorrect_marketplace(data, marketplace, expected):
    """
    Test the replace_incorrect_marketplace function.

    Given:
        - A data object (string, dict, or list).
        - A marketplace version.

    When:
        - The function is called to replace all occurrences of "Cortex XSOAR" with "Cortex" if the marketplace is MarketplaceV2 or XPANSE.
        - If the word following "Cortex XSOAR" contains a number, it will also be removed.

    Then:
        - The function should return the data with the replacements made if applicable.
    """
    result = replace_incorrect_marketplace(data, marketplace, path="example/path")
    assert result == expected


def test_replace_incorrect_marketplace_error_handling():
    """
    Test the error handling of the replace_incorrect_marketplace function.

    Given:
        - A data object that causes an exception.
        - A marketplace version.

    When:
        - The function is called and an exception occurs.

    Then:
        - The function should return the original data.
        - An error message should be logged.
    """
    data = {"key": "value"}
    marketplace = MarketplaceVersions.MarketplaceV2

    with patch(
        "demisto_sdk.commands.content_graph.common.replace_incorrect_marketplace",
        side_effect=Exception("Test exception"),
    ):
        with patch("demisto_sdk.commands.content_graph.common.logger") as mock_logger:
            result = replace_incorrect_marketplace(
                data, marketplace, path="example/path"
            )

    assert result == data
    mock_logger.error.assert_called_once_with(
        "Error processing data for replacing incorrect marketplace at path 'example/path': Test exception"
    )
