from unittest.mock import patch

import pytest
from ruamel.yaml.scalarstring import (  # noqa: TID251 - only importing FoldedScalarString is OK
    FoldedScalarString,
)

from demisto_sdk.commands.content_graph.common import (
    ContentType,
    MarketplaceVersions,
    replace_marketplace_references,
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
        pytest.param(
            "This is a Cortex XSOAR v8.7 example.",
            MarketplaceVersions.MarketplaceV2,
            "This is a Cortex example.",
            id="Replace v8.7 with Xsaim in string",
        ),
        pytest.param(
            "This is a Cortex XSOAR v6.6.8 example.",
            MarketplaceVersions.XPANSE,
            "This is a Cortex example.",
            id="Replace v6.6.8 with Xpanse in string",
        ),
        pytest.param(
            "This is a Cortex XSOAR example of Cortex XSOAR V8.",
            MarketplaceVersions.MarketplaceV2,
            "This is a Cortex example of Cortex",
            id="Replace multiple Cortex XSOAR with Cortex",
        ),
        pytest.param(
            "This is a Cortex XSOAR example.",
            MarketplaceVersions.XSOAR,
            "This is a Cortex XSOAR example.",
            id="No replacement for Xsoar",
        ),
        pytest.param(
            "This is a Cortex XSOAR 8.7 example with https nearby and a Cortex XSOAR 8.7 example with link far away..................................... https",
            MarketplaceVersions.MarketplaceV2,
            "This is a Cortex XSOAR 8.7 example with https nearby and a Cortex example with link far away..................................... https",
            id="https near and for away",
        ),
        pytest.param(
            "This is a Cortex XSOAR 8.7 example with link far away..................................... https",
            MarketplaceVersions.MarketplaceV2,
            "This is a Cortex example with link far away..................................... https",
            id="Replace with far https",
        ),
        pytest.param(
            "This is just some random text with XSOAR only.",
            MarketplaceVersions.MarketplaceV2,
            "This is just some random text with XSOAR only.",
            id="No replace in random text",
        ),
        pytest.param(
            "This is a Cortex xsoar v6.6.8 example.",
            MarketplaceVersions.MarketplaceV2,
            "This is a Cortex xsoar v6.6.8 example.",
            id="No replace for case insensitive",
        ),
    ],
)
def test_replace_marketplace_references_strings(data, marketplace, expected):
    """
    Tests the replacement of Cortex XSOAR references in string data.
    Ensures that different versions and formats are correctly replaced or retained.
    """
    result = replace_marketplace_references(data, marketplace, path="example/path")
    assert result == expected


@pytest.mark.parametrize(
    "data, marketplace, expected",
    [
        pytest.param(
            ["This is a Cortex XSOAR v8.7 example."],
            MarketplaceVersions.MarketplaceV2,
            ["This is a Cortex example."],
            id="Replace v8.7 with Xsaim in list",
        ),
        pytest.param(
            ["This is a Cortex XSOAR V6.6.8 example."],
            MarketplaceVersions.XPANSE,
            ["This is a Cortex example."],
            id="Replace v6.6.8 with Xpanse in list",
        ),
        pytest.param(
            ["This is a Cortex XSOAR example of Cortex XSOAR V8."],
            MarketplaceVersions.MarketplaceV2,
            ["This is a Cortex example of Cortex"],
            id="Replace multiple Cortex XSOAR in list",
        ),
        pytest.param(
            ["This is a Cortex XSOAR example."],
            MarketplaceVersions.XSOAR,
            ["This is a Cortex XSOAR example."],
            id="No replacement for Xsoar in list",
        ),
        pytest.param(
            ["This is a Cortex XSOAR 8.7 example with https nearby"],
            MarketplaceVersions.MarketplaceV2,
            ["This is a Cortex XSOAR 8.7 example with https nearby"],
            id="No replace when https is nearby in list",
        ),
        pytest.param(
            [
                "This is a Cortex XSOAR 8.7 example with link far away..................................... https"
            ],
            MarketplaceVersions.MarketplaceV2,
            [
                "This is a Cortex example with link far away..................................... https"
            ],
            id="Replace with far https in list",
        ),
        pytest.param(
            ["This is just some random text with Cortex only"],
            MarketplaceVersions.MarketplaceV2,
            ["This is just some random text with Cortex only"],
            id="No replace in random text list",
        ),
        pytest.param(
            ["This is a cortex xsoar v6.6.8 example."],
            MarketplaceVersions.MarketplaceV2,
            ["This is a cortex xsoar v6.6.8 example."],
            id="No replace for case insensitive in list",
        ),
        pytest.param(
            ["This is a Cortex XSOAR/8."],
            MarketplaceVersions.MarketplaceV2,
            ["This is a Cortex XSOAR/8."],
            id="No replace within word in list ",
        ),
    ],
)
def test_replace_marketplace_references_lists(data, marketplace, expected):
    """
    Tests the replacement of Cortex XSOAR references in list data.
    Ensures the function modifies elements in the list without creating a new object.
    """
    original_id = id(data)
    result = replace_marketplace_references(data, marketplace, path="example/path")
    assert id(result) == original_id
    assert result == expected
    assert isinstance(result, list)


@pytest.mark.parametrize(
    "data, marketplace, expected",
    [
        pytest.param(
            {"key": "This is a Cortex XSOAR v8.7 example."},
            MarketplaceVersions.MarketplaceV2,
            {"key": "This is a Cortex example."},
            id="Replace v8.7 with Xsaim in dict",
        ),
        pytest.param(
            {"key": "This is a Cortex XSOAR v6.6.8 example."},
            MarketplaceVersions.XPANSE,
            {"key": "This is a Cortex example."},
            id="Replace v6.6.8 with Xpanse in dict",
        ),
        pytest.param(
            {"key": "This is a Cortex XSOAR example."},
            MarketplaceVersions.MarketplaceV2,
            {"key": "This is a Cortex example."},
            id="Replace general Cortex XSOAR in dict",
        ),
        pytest.param(
            {"key": "This is a Cortex XSOAR example."},
            MarketplaceVersions.XSOAR,
            {"key": "This is a Cortex XSOAR example."},
            id="No replacement for Xsoar in dict",
        ),
        pytest.param(
            {"key": "This is a Cortex XSOAR 8.7 example with https nearby"},
            MarketplaceVersions.MarketplaceV2,
            {"key": "This is a Cortex XSOAR 8.7 example with https nearby"},
            id="No replace when https is nearby in dict",
        ),
        pytest.param(
            {
                "key": "This is a Cortex XSOAR 8.7 example with link far away..................................... https"
            },
            MarketplaceVersions.MarketplaceV2,
            {
                "key": "This is a Cortex example with link far away..................................... https"
            },
            id="Replace with far https in dict",
        ),
        pytest.param(
            {"key": "This is just some random text with Cortex only"},
            MarketplaceVersions.MarketplaceV2,
            {"key": "This is just some random text with Cortex only"},
            id="No replace in random text dict",
        ),
        pytest.param(
            {"key": "This is a cortex xsoar v6.6.8 example."},
            MarketplaceVersions.MarketplaceV2,
            {"key": "This is a cortex xsoar v6.6.8 example."},
            id="No replace for case insensitive in dict",
        ),
        pytest.param(
            {"This is a Cortex XSOAR v8.7 example.": "Some value"},
            MarketplaceVersions.MarketplaceV2,
            {"This is a Cortex example.": "Some value"},
            id="Replace key in dict (v8.7)",
        ),
        pytest.param(
            {"This is a Cortex XSOAR v6.6.8 example.": "Another value"},
            MarketplaceVersions.XPANSE,
            {"This is a Cortex example.": "Another value"},
            id="Replace key in dict (v6.6.8)",
        ),
        pytest.param(
            {"This is a Cortex XSOAR example.": "Value here"},
            MarketplaceVersions.MarketplaceV2,
            {"This is a Cortex example.": "Value here"},
            id="Replace key in dict (general)",
        ),
        pytest.param(
            {
                "key": [
                    "This is a Cortex XSOAR v8.7 example.",
                    "Another Cortex XSOAR v6.6.8 example.",
                ]
            },
            MarketplaceVersions.MarketplaceV2,
            {"key": ["This is a Cortex example.", "Another Cortex example."]},
            id="Replace values in list in dict",
        ),
        # Test with FoldedScalarString
        pytest.param(
            {
                "description": "This is a Cortex XSOAR example.",
                "details": "Cortex XSOAR should be replaced.",
                "folded": FoldedScalarString(
                    "Cortex XSOAR should be replaced in FoldedScalarString."
                ),
            },
            MarketplaceVersions.MarketplaceV2,
            {
                "description": "This is a Cortex example.",
                "details": "Cortex should be replaced.",
                "folded": FoldedScalarString(
                    "Cortex should be replaced in FoldedScalarString."
                ),
            },
            id="Replace in dict with FoldedScalarString intact",
        ),
    ],
)
def test_replace_marketplace_references_dicts(data, marketplace, expected):
    """
    Tests the replacement of Cortex XSOAR references in dictionary data.
    Ensures values and keys are replaced while maintaining object identity.
    """
    original_id = id(data)

    if isinstance(data.get("folded"), FoldedScalarString):
        original_type = type(data["folded"])

    result = replace_marketplace_references(data, marketplace, path="example/path")

    assert id(result) == original_id
    assert result == expected

    if result.get("folded") and isinstance(result.get("folded"), FoldedScalarString):
        assert isinstance(result["folded"], original_type)


def test_replace_marketplace_references__error_handling():
    """
    Test the error handling of the replace_marketplace_references function.

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
        "demisto_sdk.commands.content_graph.common.replace_marketplace_references",
        side_effect=Exception("Test exception"),
    ):
        with patch("demisto_sdk.commands.content_graph.common.logger") as mock_logger:
            result = replace_marketplace_references(
                data, marketplace, path="example/path"
            )

    assert result == data
    mock_logger.error.assert_called_once_with(
        "Error processing data for replacing incorrect marketplace at path 'example/path': Test exception"
    )
