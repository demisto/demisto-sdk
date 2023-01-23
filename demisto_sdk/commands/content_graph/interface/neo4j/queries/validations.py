from typing import List, Tuple

from neo4j import Transaction, graph

from demisto_sdk.commands.content_graph.common import (
    ContentType,
    Neo4jRelationshipResult,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
    run_query,
    versioned,
)


def validate_unknown_content(tx: Transaction, file_paths: List[str]):
    file_paths_filter = (
        f"WHERE content_item_from.path in {file_paths}" if file_paths else ""
    )
    query = f"""
        // Returning all the USES relationships where the target is not in the repository
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


def validate_fromversion(tx: Transaction, file_paths: List[str], from_version: bool):
    file_paths_filter = (
        f"AND content_item_from.path in {file_paths}" if file_paths else ""
    )
    from_version_filter = (
        f"AND {versioned('content_item_from.fromversion')} >= toIntegerList([6,5,0])"
        if from_version
        else f"AND toIntegerList([6,5,0]) > {versioned('content_item_from.fromversion')}"
    )

    query = f"""
        // Returning all the USES relationships with where the target's to_version is bigger than the source's
        MATCH (content_item_from)-[r:{RelationshipType.USES}{{mandatorily:true}}]->(n)
        WHERE {versioned('content_item_from.fromversion')} < {versioned('n.fromversion')}
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


def validate_toversion(tx: Transaction, file_paths: List[str], to_version: bool):
    file_paths_filter = (
        f"AND content_item_from.path in {file_paths}" if file_paths else ""
    )
    from_version_filter = (
        f"AND {versioned('content_item_from.toversion')} >= toIntegerList([6,5,0])"
        if to_version
        else f"AND toIntegerList([6,5,0]) > {versioned('content_item_from.toversion')}"
    )
    query = f"""
        // Returning all the USES relationships with where the target's to_version is smaller than the source's
        MATCH (content_item_from)-[r:{RelationshipType.USES}{{mandatorily: true}}]->(n)
        WHERE {versioned('content_item_from.toversion')} > {versioned('n.toversion')}
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


def validate_marketplaces(tx: Transaction, file_paths: List[str]):
    file_paths_filter = (
        f"AND content_item_from.path in {file_paths}" if file_paths else ""
    )
    query = f"""
        // Returning all the USES relationships with where the target's marketplaces doesn't include all of the source's marketplaces
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


def validate_multiple_packs_with_same_display_name(
    tx: Transaction, file_paths: List[str]
) -> List[Tuple[graph.Node, List[graph.Node]]]:
    file_paths_filter = f"AND a.path in {file_paths}" if file_paths else ""

    query = f"""
        // Returning all the packs that have the same name but different id
        MATCH (a:{ContentType.PACK}), (b:{ContentType.PACK})
        WHERE a.name = b.name
        {file_paths_filter}
        AND id(a) <> id(b)
        RETURN a.object_id AS a_object_id, collect(b.object_id) AS b_object_ids
        """
    return [
        (item.get("a_object_id"), item.get("b_object_ids"))
        for item in run_query(tx, query)
    ]
