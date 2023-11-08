from time import sleep
from typing import List

from neo4j import Transaction

from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import run_query


def import_graphml(tx: Transaction, graphml_filenames: List[str]) -> None:
    for filename in graphml_filenames:
        query = f'CALL apoc.import.graphml("file:/{filename}", {{readLabels: true}})'
        run_query(tx, query)


def export_graphml(tx: Transaction, repo_name: str) -> None:
    sleep(1)  # doesn't work without it
    query = f'CALL apoc.export.graphml.all("{repo_name}.graphml", {{useTypes: true}})'
    run_query(tx, query)
