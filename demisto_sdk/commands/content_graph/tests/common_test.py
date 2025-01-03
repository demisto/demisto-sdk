from unittest.mock import patch

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


def test_replace_marketplace_references_string_with_number():
    """
    Test the replace_marketplace_references function with a string containing a number.

    Given:
        - A string data object.
        - A marketplace version.

    When:
        - The function is called to replace all occurrences of "Cortex XSOAR" with "Cortex" if the marketplace is MarketplaceV2 or XPANSE.
        - If the word following "Cortex XSOAR" contains a number, it will also be removed.

    Then:
        - The function should return the data with the replacements made if applicable.
    """
    data = "This is a Cortex XSOAR v1 example."
    expected = "This is a Cortex example."
    result = replace_marketplace_references(
        data, MarketplaceVersions.MarketplaceV2, path="example/path"
    )
    assert result == expected


def test_replace_marketplace_references__string_without_number():
    """
    Test the replace_marketplace_references function with a string not containing a number.

    Given:
        - A string data object.
        - A marketplace version.

    When:
        - The function is called to replace all occurrences of "Cortex XSOAR" with "Cortex" if the marketplace is MarketplaceV2 or XPANSE.

    Then:
        - The function should return the data with the replacements made if applicable.
    """
    data = "This is a Cortex XSOAR example."
    expected = "This is a Cortex example."
    result = replace_marketplace_references(
        data, MarketplaceVersions.MarketplaceV2, path="example/path"
    )
    assert result == expected


def test_replace_marketplace_references__string_no_replacement():
    """
    Test the replace_marketplace_references function with a string where no replacement should occur in the specific marketplace..

    Given:
        - A string data object.
        - A marketplace version.

    When:
        - The function is called to replace all occurrences of "Cortex XSOAR" with "Cortex" if the marketplace is MarketplaceV2 or XPANSE.

    Then:
        - The function should return the data with the replacements made if applicable.
    """
    data = "This is a Cortex XSOAR v1 example."
    expected = "This is a Cortex XSOAR v1 example."
    result = replace_marketplace_references(
        data, MarketplaceVersions.XSOAR, path="example/path"
    )
    assert result == expected


def test_replace_marketplace_references__dict():
    """
    Test the replace_marketplace_references function with a dictionary.

    Given:
        - A dictionary data object.
        - A marketplace version (MarketplaceV2 or XPANSE).

    When:
        - The function is called to replace all occurrences of "Cortex XSOAR" with "Cortex".
        - If the word following "Cortex XSOAR" contains a number, it will also be removed.

    Then:
        - The function should return the data with the replacements made if applicable.
        - The function should modify the data in place and not create a copy.
        - The type of FoldedScalarString values should be preserved.
    """
    data = {
        "description": "This is a Cortex XSOAR v1 example.",
        "details": "Cortex XSOAR should be replaced.",
        "Cortex XSOAR": "Cortex XSOAR",
        "folded": FoldedScalarString(
            "Cortex XSOAR should be replaced in FoldedScalarString."
        ),
    }
    original_id = id(data)
    expected = {
        "description": "This is a Cortex example.",
        "details": "Cortex should be replaced.",
        "Cortex": "Cortex",
        "folded": FoldedScalarString(
            "Cortex should be replaced in FoldedScalarString."
        ),
    }
    result = replace_marketplace_references(
        data, MarketplaceVersions.MarketplaceV2, path="example/path"
    )
    assert id(result) == original_id
    assert result == expected
    assert isinstance(result["folded"], FoldedScalarString)


def test_replace_marketplace_references__list():
    """
    Test the replace_marketplace_references function with a list containing strings and dictionaries.

    Given:
        - A list data object containing strings and dictionaries.
        - A marketplace version (MarketplaceV2 or XPANSE).

    When:
        - The function is called to replace all occurrences of "Cortex XSOAR" with "Cortex".
        - If the word following "Cortex XSOAR" contains a number, it will also be removed.

    Then:
        - The function should return the data with the replacements made if applicable.
        - The function should modify the data in place and not create a copy.
    """
    data = [
        "This is a Cortex XSOAR v1 example.",
        "Cortex XSOAR should be replaced.",
        {
            "description": "This is a Cortex XSOAR v2 example.",
            "details": "Cortex XSOAR should be replaced in details.",
        },
        {"nested_list": ["Cortex XSOAR v3 example.", "Another Cortex XSOAR example."]},
    ]
    original_id = id(data)
    expected = [
        "This is a Cortex example.",
        "Cortex should be replaced.",
        {
            "description": "This is a Cortex example.",
            "details": "Cortex should be replaced in details.",
        },
        {"nested_list": ["Cortex example.", "Another Cortex example."]},
    ]
    result = replace_marketplace_references(
        data, MarketplaceVersions.MarketplaceV2, path="example/path"
    )
    assert id(result) == original_id
    assert result == expected


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
