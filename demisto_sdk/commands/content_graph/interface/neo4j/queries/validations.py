from typing import List, Tuple

from neo4j import Transaction

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    GENERAL_DEFAULT_FROMVERSION,
)
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
    query = f"""// Returns USES relationships to content items not in the repository
MATCH (content_item_from{{deprecated: false}})-[r:{RelationshipType.USES}]->(n{{not_in_repository:true}})
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


def validate_fromversion(
    tx: Transaction, file_paths: List[str], for_supported_versions: bool
):
    op = ">=" if for_supported_versions else "<"
    query = f"""// Returning all the USES relationships with where the target's fromversion is higher than the source's
MATCH (content_item_from{{deprecated: false}})-[r:{RelationshipType.USES}{{mandatorily:true}}]->(n)
WHERE {versioned('content_item_from.fromversion')} < {versioned('n.fromversion')}
AND {versioned('n.fromversion')} {op} {versioned(GENERAL_DEFAULT_FROMVERSION)}
AND n.fromversion <> "{DEFAULT_CONTENT_ITEM_FROM_VERSION}"  // skips types with no "fromversion"
"""
    if file_paths:
        query += f"AND content_item_from.path in {file_paths}"
    query += f"""
OPTIONAL MATCH (n2{{object_id: n.object_id, content_type: n.content_type}})
WHERE id(n) <> id(n2)
AND {versioned('content_item_from.fromversion')} >= {versioned('n2.fromversion')}

WITH content_item_from, r, n, n2
WHERE NOT exists((content_item_from)-[:{RelationshipType.USES}{{mandatorily:true}}]->(n2))
RETURN content_item_from, collect(r) as relationships, collect(n) as nodes_to"""
    return {
        int(item.get("content_item_from").id): Neo4jRelationshipResult(
            node_from=item.get("content_item_from"),
            relationships=item.get("relationships"),
            nodes_to=item.get("nodes_to"),
        )
        for item in run_query(tx, query)
    }


def validate_toversion(
    tx: Transaction, file_paths: List[str], for_supported_versions: bool
):
    op = ">=" if for_supported_versions else "<"
    query = f"""// Returning all the USES relationships with where the target's toversion is lower than the source's
MATCH (content_item_from{{deprecated: false}})-[r:{RelationshipType.USES}{{mandatorily:true}}]->(n)
WHERE {versioned('content_item_from.toversion')} > {versioned('n.toversion')}
AND {versioned('content_item_from.toversion')} {op} {versioned(GENERAL_DEFAULT_FROMVERSION)}
"""
    if file_paths:
        query += f"AND content_item_from.path in {file_paths}"
    query += f"""
OPTIONAL MATCH (n2{{object_id: n.object_id, content_type: n.content_type}})
WHERE id(n) <> id(n2)
AND {versioned('content_item_from.toversion')} <= {versioned('n2.toversion')}

WITH content_item_from, r, n, n2
WHERE NOT exists((content_item_from)-[:{RelationshipType.USES}{{mandatorily:true}}]->(n2))
RETURN content_item_from, collect(r) as relationships, collect(n) as nodes_to"""
    return {
        int(item.get("content_item_from").id): Neo4jRelationshipResult(
            node_from=item.get("content_item_from"),
            relationships=item.get("relationships"),
            nodes_to=item.get("nodes_to"),
        )
        for item in run_query(tx, query)
    }


def validate_marketplaces(tx: Transaction, file_paths: List[str]):
    query = f"""// Returns all the USES relationships with where the target's marketplaces doesn't include all of the source's marketplaces
MATCH (content_item_from{{deprecated: false}})-[r:{RelationshipType.USES}{{mandatorily:true}}]->(n)
WHERE not all(elem IN content_item_from.marketplaces WHERE elem IN n.marketplaces)
"""
    if file_paths:
        query += f"AND content_item_from.path in {file_paths}"
    query += f"""
OPTIONAL MATCH (n2{{object_id: n.object_id, content_type: n.content_type}})
WHERE id(n) <> id(n2)
AND all(elem IN content_item_from.marketplaces WHERE elem IN n2.marketplaces)

WITH content_item_from, r, n, n2
WHERE NOT exists((content_item_from)-[:{RelationshipType.USES}{{mandatorily:true}}]->(n2))
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
) -> List[Tuple[str, List[str]]]:
    query = f"""// Returns all the packs that have the same name but different id
MATCH (a:{ContentType.PACK}), (b:{ContentType.PACK})
WHERE a.name = b.name
"""
    if file_paths:
        query += f"AND a.path in {file_paths}"
    query += """
AND id(a) <> id(b)
RETURN a.object_id AS a_object_id, collect(b.object_id) AS b_object_ids
"""
    return [
        (item.get("a_object_id"), item.get("b_object_ids"))
        for item in run_query(tx, query)
    ]


def validate_dependencies(
    tx: Transaction, pack_ids: List[str], core_pack_list: List[str]
):

    query = f"""// Returns DEPENDS_ON relationships to content items who are not core packs
    MATCH (content_item_from)-[r:DEPENDS_ON{{mandatorily:true}}]->(n)
    WHERE content_item_from.object_id in {pack_ids}
    AND NOT r.is_test
    AND NOT n.object_id IN {core_pack_list}
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
