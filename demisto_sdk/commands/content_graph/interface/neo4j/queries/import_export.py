from time import sleep
from typing import List

from neo4j import Transaction

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import run_query


def import_graphml(tx: Transaction, graphml_filenames: List[str]) -> None:
    for filename in graphml_filenames:
        query = f'CALL apoc.import.graphml("file:/{filename}", {{readLabels: true}})'
        run_query(tx, query)


def export_graphml(tx: Transaction, repo_name: str) -> None:
    sleep(1)  # doesn't work without it
    query = f'CALL apoc.export.graphml.all("{repo_name}.graphml", {{useTypes: true}})'
    run_query(tx, query)


def merge_duplicate_commands(tx: Transaction) -> None:
    run_query(
        tx,
        """// Merges possible duplicate command nodes after import
MATCH (c:Command)
WITH c.object_id as object_id, collect(c) as cmds
CALL apoc.refactor.mergeNodes(cmds, {properties: "combine", mergeRels: true}) YIELD node
RETURN node""",
    )


def merge_duplicate_content_items(tx: Transaction) -> None:
    run_query(
        tx,
        f"""// Merges possible duplicate content item nodes after import
MATCH (n:{ContentType.BASE_NODE}{{not_in_repository: true}})
MATCH (m:{ContentType.BASE_NODE}{{content_type: n.content_type}})
WHERE ((m.object_id = n.object_id AND m.object_id <> "") OR (m.name = n.name AND m.name <> ""))
AND m.not_in_repository = false
WITH m, n
CALL apoc.refactor.mergeNodes([m, n], {{properties: "discard", mergeRels: true}}) YIELD node
RETURN node""",
    )
