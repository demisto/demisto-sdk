import logging
from pathlib import Path
from typing import List

from neo4j import Transaction

from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import run_query
from demisto_sdk.commands.content_graph.interface.neo4j.queries.constraints import \
    create_constraints, drop_constraints

logger = logging.getLogger('demisto-sdk')

REPO_NAME = Path.cwd().name
CONVERT_MARKETPLACES_FIELD_TO_STRING = """MATCH (n) WHERE NOT n.marketplaces IS NULL
SET n.marketplaces = apoc.text.join(n.marketplaces, "$")
RETURN n
"""
CONVERT_MARKETPLACES_FIELD_TO_LIST = """MATCH (n) WHERE NOT n.marketplaces IS NULL
SET n.marketplaces = split(n.marketplaces, "$")
RETURN n
"""
EXPORT_ALL_QUERY = f'call apoc.export.csv.all("{REPO_NAME}.csv", {{bulkImport: true}})'


def pre_export_write_queries(tx: Transaction) -> None:
    run_query(tx, CONVERT_MARKETPLACES_FIELD_TO_STRING)


def export_to_csv(
    tx: Transaction,
) -> None:
    run_query(tx, EXPORT_ALL_QUERY)


def post_export_write_queries(tx: Transaction) -> None:
    run_query(tx, CONVERT_MARKETPLACES_FIELD_TO_LIST)


def get_nodes_files_to_import(import_path: Path):
    nodes_files: List[str] = []
    for file in import_path.iterdir():
        filename = file.name
        if '.nodes.' in filename:
            nodes_files.append(f'{{fileName: "file:/{filename}", labels: []}}')
    return f'{", ".join(nodes_files)}'


def get_relationships_files_to_import(import_path: Path):
    relationships_files: List[str] = []
    for file in import_path.iterdir():
        filename = file.name
        if '.relationships.' in filename:
            relationships_files.append(f'{{fileName: "file:/{filename}", type: null}}')
    return f'{", ".join(relationships_files)}'


def pre_import_write_queries(
    tx: Transaction,
) -> None:
    pass


def pre_import_schema_queries(
    tx: Transaction,
) -> None:
    drop_constraints(tx)


def import_csv(
    tx: Transaction,
    import_path: Path,
) -> None:
    nodes_files = get_nodes_files_to_import(import_path)
    relationships_files = get_relationships_files_to_import(import_path)
    run_query(tx, f'CALL apoc.import.csv([{nodes_files}], [{relationships_files}], {{}})')


def post_import_write_queries(
    tx: Transaction,
) -> None:
    remove_unused_properties(tx)
    run_query(tx, CONVERT_MARKETPLACES_FIELD_TO_LIST)
    fix_description_property(tx)
    # handle_duplicates(tx)


def post_import_schema_queries(tx: Transaction) -> None:
    create_constraints(tx)


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


def handle_duplicates(tx: Transaction) -> None:
    merge_duplicate_commands(tx)
    merge_duplicate_content_items(tx)


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
