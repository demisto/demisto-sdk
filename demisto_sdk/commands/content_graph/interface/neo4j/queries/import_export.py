import logging
from typing import List

from neo4j import Transaction

from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import run_query

logger = logging.getLogger('demisto-sdk')

LIST_PROPERTIES = [
    'marketplaces',
    'tags',
    'categories',
    'use_cases',
    'keywords',
    'packs',
    'integrations',
    'scripts'
]

CONVERT_FIELD_TO_STRING = """MATCH (n) WHERE NOT n.{prop} IS NULL
SET n.{prop} = apoc.text.join(n.{prop}, "$")
RETURN n
"""
CONVERT_FIELD_TO_LIST = """MATCH (n) WHERE NOT n.{prop} IS NULL
SET n.{prop} = CASE n.{prop} WHEN "" THEN [] ELSE split(n.{prop}, "$") END
RETURN n
"""


def pre_export_write_queries(tx: Transaction) -> None:
    for prop in LIST_PROPERTIES:
        run_query(tx, CONVERT_FIELD_TO_STRING.format(prop=prop))


def export_to_csv(tx: Transaction, repo_name: str) -> None:
    query = f'call apoc.export.csv.all("{repo_name}.csv", {{bulkImport: true}})'
    run_query(tx, query)


def post_export_write_queries(tx: Transaction) -> None:
    for prop in LIST_PROPERTIES:
        run_query(tx, CONVERT_FIELD_TO_LIST.format(prop=prop))


def pre_import_write_queries(
    tx: Transaction,
) -> None:
    pass


def import_csv(tx: Transaction, node_files: List[str], relationship_files: List[str]) -> None:
    nodes_files = ", ".join([
        f'{{fileName: "file:/{filename}", labels: []}}'
        for filename in node_files
    ])
    relationship_files = ", ".join([
        f'{{fileName: "file:/{filename}", type: null}}'
        for filename in relationship_files
    ])
    run_query(tx, f'CALL apoc.import.csv([{nodes_files}], [{relationship_files}], {{}})')


def post_import_write_queries(
    tx: Transaction,
) -> None:
    remove_unused_properties(tx)
    for prop in LIST_PROPERTIES:
        run_query(tx, CONVERT_FIELD_TO_LIST.format(prop=prop))
    fix_description_property(tx)


def remove_unused_properties(tx: Transaction) -> None:
    run_query(tx, 'MATCH (n) REMOVE n.__csv_id')
    run_query(tx, 'MATCH ()-[r]->() REMOVE r.__csv_type')


def fix_description_property(tx: Transaction) -> None:
    run_query(tx, """MATCH ()-[r:HAS_COMMAND]->()
SET r.description =
CASE
  WHEN r["description\r"] IS NULL THEN r.description
  ELSE r["description\r"]
END
WITH r
CALL apoc.create.removeRelProperties(r, ["description\r"])
YIELD rel
RETURN *""")


def merge_duplicate_commands(tx: Transaction) -> None:
    run_query(tx, """MATCH (c:Command)
WITH c.object_id as object_id, collect(c) as cmds
CALL apoc.refactor.mergeNodes(cmds, {properties: "combine", mergeRels: true}) YIELD node
RETURN node
""")


def temporarily_set_not_in_repository(tx: Transaction) -> None:
    run_query(tx, """MATCH (n) WHERE n.not_in_repository IS NULL
SET n.not_in_repository = false
RETURN n
""")


def merge_duplicate_content_items(tx: Transaction) -> None:
    run_query(tx, """MATCH (n:BaseContent{not_in_repository: true})
MATCH (m:BaseContent{content_type: n.content_type})
WHERE ((m.object_id = n.object_id AND m.object_id <> "") OR (m.name = n.name AND m.name <> ""))
AND m.not_in_repository = false
WITH m, n
CALL apoc.refactor.mergeNodes([m, n], {properties: "discard", mergeRels: true}) YIELD node
RETURN node
""")


def remove_not_in_repository(tx: Transaction) -> None:
    run_query(tx, """MATCH (n{not_in_repository: false})
REMOVE n.not_in_repository
RETURN n
""")
