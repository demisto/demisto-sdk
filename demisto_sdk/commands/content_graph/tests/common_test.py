from demisto_sdk.commands.content_graph.common import ContentType


def test_content_type_does_not_contain_colon():
    """
    A colon is a special character in neo4j Cypher indicates when the label starts in the query, e.g.:
    `MATCH (n:Integration) return n`
    We want to make sure there are no colons in all content type values.
    """

    for content_type in ContentType:
        assert ":" not in content_type.value
