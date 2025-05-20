from typing import Dict, List, Tuple

from more_itertools import first
from neo4j import Transaction, graph

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    GENERAL_DEFAULT_FROMVERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import replace_alert_to_incident
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


def validate_unknown_content(tx: Transaction, file_paths: List[str]):
    """Query graph to return all ids used in the provided files that are missing from the repo.

    Args:
        tx: The Transaction to contact the graph with.
        file_paths: The file paths to check
    Return:
        All content ids used in the provided file paths that are missing from the repo.
    """
    query = f"""// Returns USES relationships to content items not in the repository
        MATCH (content_item_from{{deprecated: false}})-[r:{RelationshipType.USES}]->(n{{not_in_repository: true}})
        {f'WHERE content_item_from.path in {file_paths}' if file_paths else ''}
        RETURN content_item_from, collect(r) as relationships, collect(n) as nodes_to
        """
    return {
        item.get("content_item_from").element_id: Neo4jRelationshipResult(
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
MATCH (content_item_from{{deprecated: false, is_test: false}})-[r:{RelationshipType.USES}{{mandatorily:true}}]->(n)
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
WHERE elementId(n) <> elementId(n2)
AND {versioned('content_item_from.fromversion')} >= {versioned('n2.fromversion')}

WITH content_item_from, r, n, n2
WHERE NOT exists((content_item_from)-[:{RelationshipType.USES}{{mandatorily:true}}]->(n2))
RETURN content_item_from, collect(r) as relationships, collect(n) as nodes_to"""
    return {
        item.get("content_item_from").element_id: Neo4jRelationshipResult(
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
WHERE elementId(n) <> elementId(n2)
AND {versioned('content_item_from.toversion')} <= {versioned('n2.toversion')}

WITH content_item_from, r, n, n2
WHERE NOT exists((content_item_from)-[:{RelationshipType.USES}{{mandatorily:true}}]->(n2))
RETURN content_item_from, collect(r) as relationships, collect(n) as nodes_to"""
    return {
        item.get("content_item_from").element_id: Neo4jRelationshipResult(
            node_from=item.get("content_item_from"),
            relationships=item.get("relationships"),
            nodes_to=item.get("nodes_to"),
        )
        for item in run_query(tx, query)
    }


def get_items_using_deprecated(
    tx: Transaction, file_paths: List[str]
) -> List[Tuple[str, List[graph.Node]]]:
    return get_items_using_deprecated_commands(
        tx, file_paths
    ) + get_items_using_deprecated_content_items(tx, file_paths)


def get_items_using_deprecated_commands(
    tx: Transaction, file_paths: List[str]
) -> List[Tuple[str, List[graph.Node]]]:
    files_filter = f"AND p.path IN {file_paths}" if file_paths else ""

    command_query = f"""// Returning all the items which using deprecated commands
MATCH (p{{deprecated: false}})-[:USES]->(c:Command)<-[:HAS_COMMAND{{deprecated: true}}]-(i:Integration) WHERE NOT p.is_test
OPTIONAL MATCH (i2:Integration)-[:HAS_COMMAND{{deprecated: false}}]->(c)
WHERE elementId(i) <> elementId(i2)
WITH p, c, i2
WHERE i2 IS NULL
{files_filter}
RETURN c.object_id AS deprecated_command, collect(p) AS object_using_deprecated"""
    return [
        (
            item.get("deprecated_command"),
            item.get("object_using_deprecated"),
        )
        for item in run_query(tx, command_query)
    ]


def get_items_using_deprecated_content_items(
    tx: Transaction, file_paths: List[str]
) -> List[Tuple[str, List[graph.Node]]]:
    files_filter = f"AND p.path IN {file_paths}" if file_paths else ""

    query = f"""
    MATCH (p{{deprecated: false}})-[:USES]->(d{{deprecated: true}}) WHERE not p.is_test
// be sure the USES relationship is not because a command, as commands has dedicated query
OPTIONAL MATCH (p)-[:USES]->(c1:Command)<-[:HAS_COMMAND]-(d)
WITH p, d, c1
WHERE c1 IS NULL
{files_filter}
RETURN d.object_id AS deprecated_content, collect(p) AS object_using_deprecated
    """
    return [
        (
            item.get("deprecated_content"),
            item.get("object_using_deprecated"),
        )
        for item in run_query(tx, query)
    ]


def validate_marketplaces(tx: Transaction, pack_ids: List[str]):
    query = f"""// Returns all the USES relationships with where the target's marketplaces doesn't include all of the source's marketplaces
MATCH
(p1)<-[:{RelationshipType.IN_PACK}]-(content_item_from{{deprecated: false}})
    -[r:{RelationshipType.USES}{{mandatorily:true}}]->
        (n)-[:{RelationshipType.IN_PACK}]->(p2)
WHERE not content_item_from.is_test
AND not all(elem IN content_item_from.marketplaces WHERE elem IN n.marketplaces)
"""
    if pack_ids:
        query += f"AND (p1.object_id in {pack_ids} OR p2.object_id in {pack_ids})"
    query += f"""
OPTIONAL MATCH (n2{{object_id: n.object_id, content_type: n.content_type}})
WHERE not content_item_from.is_test
AND elementId(n) <> elementId(n2)
AND all(elem IN content_item_from.marketplaces WHERE elem IN n2.marketplaces)

WITH content_item_from, r, n, n2
WHERE NOT exists((content_item_from)-[:{RelationshipType.USES}{{mandatorily:true}}]->(n2))
RETURN content_item_from, collect(r) as relationships, collect(n) as nodes_to
"""
    return {
        item.get("content_item_from").element_id: Neo4jRelationshipResult(
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
AND elementId(a) <> elementId(b)
RETURN a.object_id AS a_object_id, collect(b.object_id) AS b_object_ids
"""
    return [
        (item.get("a_object_id"), item.get("b_object_ids"))
        for item in run_query(tx, query)
    ]


def validate_multiple_script_with_same_name(
    tx: Transaction, file_paths: List[str]
) -> Dict[str, str]:
    query = f"""// Returns all scripts that have the word 'alert' in their name
MATCH (a:{ContentType.SCRIPT})
WHERE toLower(a.name) contains "alert"
AND 'marketplacev2' IN a.marketplaces
"""
    if file_paths:
        query += f"AND a.path in {file_paths}"
    query += """
    RETURN a.name AS a_name, a.path AS a_path
    """

    content_item_names_and_paths = {
        # replace the name of the script.
        replace_alert_to_incident(item["a_name"]): item["a_path"]
        for item in run_query(tx, query)
    }

    query = f"""// Returns script names if they match the replaced name
MATCH (b:{ContentType.SCRIPT})
WHERE b.name in {list(content_item_names_and_paths.keys())}
AND NOT 'script-name-incident-to-alert' IN b.skip_prepare
AND '{MarketplaceVersions.MarketplaceV2}' IN b.marketplaces
RETURN b.name AS b_name
"""
    return {
        item["b_name"]: content_item_names_and_paths[item["b_name"]]
        for item in run_query(tx, query)
    }


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
        item.get("pack1").element_id: Neo4jRelationshipResult(
            node_from=item.get("pack1"),
            relationships=item.get("relationships"),
            nodes_to=item.get("nodes_to"),
        )
        for item in run_query(tx, query)
    }


def validate_packs_with_hidden_mandatory_dependencies(
    tx: Transaction,
    pack_ids: List[str],
) -> Dict[str, Neo4jRelationshipResult]:
    """
    Identifies non-hidden packs that have mandatory dependencies on hidden packs.
    Excludes test relationships and deprecated packs.
    Args:
        tx (Transaction): The Neo4j transaction object.
        pack_ids (List[str]): List of pack IDs to check.

    Returns:
        Dict[str, Neo4jRelationshipResult]: Dictionary of packs with hidden dependencies.
    """
    pack_filter = (
        f" AND (pack.object_id in {pack_ids} OR hidden_pack.object_id in {pack_ids})"
        if pack_ids
        else ""
    )
    query = f"""
    // Returns DEPENDS_ON relationships to packs which are hidden
    MATCH (pack:Pack {{hidden:FALSE}})-[r:{RelationshipType.DEPENDS_ON}{{mandatorily:TRUE}}]->(hidden_pack:Pack {{hidden: TRUE}})
    WHERE NOT r.is_test {pack_filter}
    RETURN pack, collect(r) as relationships, collect(hidden_pack) as nodes_to
    """
    return {
        item.get("pack").element_id: Neo4jRelationshipResult(
            node_from=item.get("pack"),
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
    WHERE elementId(content_item) <> elementId(duplicate_content_item)
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


def validate_test_playbook_in_use(
    tx: Transaction, test_playbook_ids: List[str], test_playbooks_ids_to_skip
) -> List[graph.Node]:
    query = """
MATCH (tp:TestPlaybook) WHERE
"""
    if test_playbook_ids:
        query += f" tp.object_id IN {test_playbook_ids} AND"
    query += f"""
 NOT EXISTS {{ MATCH ()-[:TESTED_BY]->(tp) }}
AND tp.deprecated = false
AND NOT (tp.object_id IN {test_playbooks_ids_to_skip})
MATCH (tp)-[:IN_PACK]->(p:Pack)
WHERE p.support = "xsoar"
AND p.deprecated = false
RETURN collect(tp) AS content_items
"""
    # when there a test playbooks that not in use, the query return a list with one item
    return first(
        filter(None, (item.get("content_items") for item in run_query(tx, query))),
        default=[],
    )
