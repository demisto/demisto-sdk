from demisto_sdk.commands.content_graph.common import ContentType
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
