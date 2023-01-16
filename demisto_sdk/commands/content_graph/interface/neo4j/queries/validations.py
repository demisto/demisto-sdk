from typing import List, Tuple

from neo4j import Transaction, graph

from demisto_sdk.commands.content_graph.common import (
    Neo4jRelationshipResult,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import run_query


def validate_unknown_content(tx: Transaction, file_paths):
    file_paths_filter = (
        f"WHERE content_item_from.path in {str(file_paths)}" if file_paths else ""
    )
    query = f"""
        MATCH (content_item_from)-[r:{RelationshipType.USES}{{mandatorily:true}}]->(n{{not_in_repository:true}})
        {file_paths_filter}
        RETURN content_item_from, collect(r) as relationships, collect(n) as nodes_to
        """
    return {
        int(item.get("content_item_from").id): Neo4jRelationshipResult(
            node_from=item.get("content_item_from"),
            relationships=item.get("relationships"),
            nodes_to=item.get("nodes_to"),
        )
        for item in run_query(tx, query)
    }


def validate_fromversion(tx: Transaction, file_paths, from_version):
    file_paths_filter = (
        f"AND content_item_from.path in {str(file_paths)}" if file_paths else ""
    )
    from_version_filter = (
        "AND toIntegerList(split(content_item_from.fromversion, '.')) >= toIntegerList([6,5,0])"
        if from_version
        else ""
    )

    query = f"""
        MATCH (content_item_from)-[r:{RelationshipType.USES}{{mandatorily:true}}]->(n)
        WHERE toIntegerList(split(content_item_from.fromversion, ".")) < toIntegerList(split(n.fromversion, "."))
        {from_version_filter}
        {file_paths_filter}
        RETURN content_item_from, collect(r) as relationships, collect(n) as nodes_to
    """
    return {
        int(item.get("content_item_from").id): Neo4jRelationshipResult(
            node_from=item.get("content_item_from"),
            relationships=item.get("relationships"),
            nodes_to=item.get("nodes_to"),
        )
        for item in run_query(tx, query)
    }


def validate_toversion(tx: Transaction, file_paths, to_version):
    file_paths_filter = (
        f"AND content_item_from.path in {str(file_paths)}" if file_paths else ""
    )
    from_version_filter = (
        "AND toIntegerList(split(content_item_from.toversion, '.')) >= toIntegerList([6,5,0])"
        if to_version
        else ""
    )
    query = f"""
        MATCH (content_item_from)-[r:{RelationshipType.USES}{{mandatorily: true}}]->(n)
        WHERE toIntegerList(split(content_item_from.toversion, ".")) < toIntegerList(split(n.toversion, "."))
        {from_version_filter}
        {file_paths_filter}
        RETURN content_item_from, collect(r) as relationships, collect(n) as nodes_to
    """
    return {
        int(item.get("content_item_from").id): Neo4jRelationshipResult(
            node_from=item.get("content_item_from"),
            relationships=item.get("relationships"),
            nodes_to=item.get("nodes_to"),
        )
        for item in run_query(tx, query)
    }


def validate_marketplaces(tx: Transaction, file_paths):
    file_paths_filter = (
        f"AND content_item_from.path in {str(file_paths)}" if file_paths else ""
    )
    query = f"""
        MATCH (content_item_from)-[r:{RelationshipType.USES}{{mandatorily:true}}]->(n)
        WHERE not all(elem IN content_item_from.marketplaces WHERE elem IN n.marketplaces)
        {file_paths_filter}
        RETURN content_item_from, collect(r) as relationships, collect(n) as nodes_to
    """
    return {
        int(item.get("content_item_from").id): Neo4jRelationshipResult(
            node_from=item.get("content_item_from"),
            relationships=item.get("relationships"),
            nodes_to=item.get("nodes_to"),
        )
        for item in run_query(tx, query)
    }


def validate_duplicate_display_name(
    tx: Transaction, pack_names: list
) -> List[Tuple[graph.Node, List[graph.Node]]]:
    pack_names_filter = f"AND a.name in {str(pack_names)}" if pack_names else ""

    query = f"""
        MATCH (a:Pack), (b:Pack)
        WHERE a.name = b.name
        {pack_names_filter}
        AND id(a) <> id(b)
        RETURN a.object_id AS a_object_id, collect(b.object_id) AS b_object_ids
        """
    return [
        (item.get("a_object_id"), item.get("b_object_ids"))
        for item in run_query(tx, query)
    ]
