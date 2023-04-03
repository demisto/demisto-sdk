from typing import List, Tuple

from neo4j import Transaction, graph

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    GENERAL_DEFAULT_FROMVERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.common import (
    ContentType,
    Neo4jRelationshipResult,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
    is_target_available,
    run_query,
    versioned,
)


def validate_unknown_content(
    tx: Transaction, file_paths: List[str], raises_error: bool
):
    query = f"""// Returns USES relationships to content items not in the repository
MATCH (content_item_from{{deprecated: false}})-[r:{RelationshipType.USES}]->(n{{not_in_repository: true}})
WHERE{' NOT' if raises_error else ''} (content_item_from.is_test OR NOT r.mandatorily)
{f'AND content_item_from.path in {file_paths}' if file_paths else ''}
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
        query += (
            f"AND (content_item_from.path in {file_paths} OR n.path in {file_paths})"
        )
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
        query += (
            f"AND (content_item_from.path in {file_paths} OR n.path in {file_paths})"
        )
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


def validate_marketplaces(tx: Transaction, pack_ids: List[str]):
    query = f"""// Returns all the USES relationships with where the target's marketplaces doesn't include all of the source's marketplaces
MATCH
(p1)<-[:{RelationshipType.IN_PACK}]-(content_item_from{{deprecated: false}})
    -[r:{RelationshipType.USES}{{mandatorily:true}}]->
        (n)-[:{RelationshipType.IN_PACK}]->(p2)
WHERE not all(elem IN content_item_from.marketplaces WHERE elem IN n.marketplaces)
"""
    if pack_ids:
        query += f"AND (p1.object_id in {pack_ids} OR p2.object_id in {pack_ids})"
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


def validate_core_packs_dependencies(
    tx: Transaction,
    pack_ids: List[str],
    marketplace: MarketplaceVersions,
    core_pack_list: List[str],
):

    query = f"""// Returns DEPENDS_ON relationships to content items who are not core packs
    MATCH (pack1)-[r:DEPENDS_ON{{mandatorily:true}}]->(pack2)
    WHERE pack1.object_id in {pack_ids}
    AND NOT r.is_test
    AND NOT pack2.object_id IN {core_pack_list}
    AND "{marketplace}" IN pack1.marketplaces
    AND "{marketplace}" IN pack2.marketplaces
    RETURN pack1, collect(r) as relationships, collect(pack2) as nodes_to
    """
    return {
        int(item.get("pack1").id): Neo4jRelationshipResult(
            node_from=item.get("pack1"),
            relationships=item.get("relationships"),
            nodes_to=item.get("nodes_to"),
        )
        for item in run_query(tx, query)
    }


def validate_duplicate_ids(
    tx: Transaction, file_paths: List[str]
) -> List[Tuple[graph.Node, List[graph.Node]]]:
    query = f"""// Returns duplicate content items with same id
    MATCH (content_item)
    MATCH (duplicate_content_item)
    WHERE id(content_item) <> id(duplicate_content_item)
    AND content_item.object_id = duplicate_content_item.object_id
    AND content_item.content_type = duplicate_content_item.content_type
    AND {is_target_available('content_item', 'duplicate_content_item')}
    {f'AND content_item.path in {file_paths}' if file_paths else ''}
    RETURN content_item, collect(duplicate_content_item) AS duplicate_content_items
    """
    return [
        (item.get("content_item"), item.get("duplicate_content_items"))
        for item in run_query(tx, query)
    ]
