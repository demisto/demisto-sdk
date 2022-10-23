from typing import List

import pytest

from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import \
    Neo4jContentGraphInterface as ContentGraphInterface
from demisto_sdk.commands.common.constants import MarketplaceVersions


class TestNeo4jQueries:
    @pytest.mark.parametrize(
        'content_type, expected_labels',
        [
            (ContentType.INTEGRATION, [ContentType.BASE_CONTENT, ContentType.INTEGRATION]),
            (ContentType.TEST_PLAYBOOK, [ContentType.BASE_CONTENT, ContentType.PLAYBOOK, ContentType.TEST_PLAYBOOK]),
            (ContentType.SCRIPT, [ContentType.BASE_CONTENT, ContentType.SCRIPT, ContentType.COMMAND_OR_SCRIPT]),
        ]
    )
    def test_labels_of(self, content_type: ContentType, expected_labels: List[ContentType]):
        """
        Given:
            - A content type enum object.
        When:
            - Calling labels_of() method.
        Then:
            - Make sure the output string has the expected content type labels.
        """
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import \
            labels_of
        integration_labels = labels_of(content_type)
        for content_type in expected_labels:
            assert str(content_type.value) in integration_labels

    def test_node_map(self):
        """
        Given:
            - A dictionary with string keys and values.
        When:
            - Calling node_map() method.
        Then:
            - Make sure the output is a string representation of a map in neo4j format.
        """
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import \
            node_map
        assert node_map({
            'object_id': 'rel_data.source_id',
            'content_type': 'rel_data.source_type',
        }) == '{object_id: rel_data.source_id, content_type: rel_data.source_type}'


class TestNeo4jInterface:

    def test_search_packs(self):
        with ContentGraphInterface() as interface:
            packs = interface.match(
                marketplace='xsoar',
                content_type=ContentType.PACK)
            integrations = interface.match(
                marketplace='xsoar',
                content_type=ContentType.INTEGRATION)
            
            # connected = interface.get_connected_nodes_by_relationship_type(
            #     'xsoar',
            #     RelationshipType.USES,
            #     content_type_from=ContentType.SCRIPT,
            #     content_type_to=ContentType.SCRIPT,
            #     recursive=True
            # )
            print()