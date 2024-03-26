from typing import List

import pytest

from demisto_sdk.commands.content_graph.common import ContentType


class TestNeo4jQueries:
    @pytest.mark.parametrize(
        "content_type, expected_labels",
        [
            (
                ContentType.INTEGRATION,
                [ContentType.BASE_NODE, ContentType.INTEGRATION],
            ),
            (
                ContentType.TEST_PLAYBOOK,
                [
                    ContentType.BASE_NODE,
                    ContentType.PLAYBOOK,
                    ContentType.TEST_PLAYBOOK,
                ],
            ),
            (
                ContentType.SCRIPT,
                [
                    ContentType.BASE_NODE,
                    ContentType.SCRIPT,
                    ContentType.COMMAND_OR_SCRIPT,
                ],
            ),
        ],
    )
    def test_labels_of(
        self, content_type: ContentType, expected_labels: List[ContentType]
    ):
        """
        Given:
            - A content type enum object.
        When:
            - Calling labels_of() method.
        Then:
            - Make sure the output string has the expected content type labels.
        """
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
            labels_of,
        )

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
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
            node_map,
        )

        assert (
            node_map(
                {
                    "object_id": "rel_data.source_id",
                    "content_type": "rel_data.source_type",
                }
            )
            == "{object_id: rel_data.source_id, content_type: rel_data.source_type}"
        )
