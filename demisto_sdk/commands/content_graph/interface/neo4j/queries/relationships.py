from pathlib import Path
from typing import Any, Dict, List, Optional

from neo4j import Transaction

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import (
    ContentType,
    Neo4jRelationshipResult,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
    labels_of,
    node_map,
    run_query,
)


def build_source_properties() -> str:
    return node_map(
        {
            "object_id": "rel_data.source_id",
            "content_type": "rel_data.source_type",
            "fromversion": "rel_data.source_fromversion",
            "marketplaces": "rel_data.source_marketplaces",
        }
    )


def build_target_properties(
    identifier: str = "object_id",
    with_content_type: bool = False,
) -> str:
    properties = {identifier: "rel_data.target"}
    if with_content_type:
        properties["content_type"] = "rel_data.target_type"
    return node_map(properties)


def build_has_command_relationships_query() -> str:
    return f"""// Creates relationships between integrations and their commands.
// Note: according to a constraint, two command nodes cannot have the same name.
UNWIND $data AS rel_data

MATCH (integration:{ContentType.INTEGRATION}{build_source_properties()})

MERGE (cmd:{ContentType.COMMAND}{build_target_properties(with_content_type=True)})

// If created, add its name and marketplaces based on the integration's property
ON CREATE
    SET cmd:{labels_of(ContentType.COMMAND)},
        cmd.marketplaces = rel_data.source_marketplaces,
        cmd.name = rel_data.name,
        cmd.not_in_repository = false

// Otherwize, add the integration's marketplaces to its marketplaces property
ON MATCH
    SET cmd.marketplaces = REDUCE(
        marketplaces = cmd.marketplaces, mp IN rel_data.source_marketplaces |
        CASE WHEN NOT mp IN cmd.marketplaces THEN marketplaces + mp ELSE marketplaces END
    )

// Create the relationship
MERGE (integration)-[r:{RelationshipType.HAS_COMMAND}{{
    deprecated: rel_data.deprecated,
    description: rel_data.description
}}]->(cmd)

RETURN count(r) AS relationships_merged"""


def build_uses_relationships_query(
    target_identifier: str = "object_id",
) -> str:
    return f"""// Creates USES relationships between parsed nodes.
// Note: if a target node is created, it means the node does not exist in the repository.
UNWIND $data AS rel_data
MATCH (source:{ContentType.BASE_NODE}{build_source_properties()})
// Get all content items with the specified properties
CALL apoc.merge.node(
    [rel_data.target_type, "{ContentType.BASE_NODE}"],
    {build_target_properties(identifier=target_identifier)},
    {{
        not_in_repository: true,
        object_id: rel_data.target,
        name: rel_data.target,
        cli_name: rel_data.target,
        content_type: rel_data.target_type
    }}
) YIELD node as target

// We want to make sure that the we need to create the relationship
// If the target node is not in the repository, we need to create the relationship only if there is not equivalent target does not exists in the repository
// If the target node is in the repository, we need to create the relationship anyway
OPTIONAL MATCH (existing_target:{ContentType.BASE_NODE}{{{target_identifier}: rel_data.target, not_in_repository: false}})
WHERE rel_data.target_type in labels(existing_target)
WITH source, target, rel_data, existing_target
WHERE existing_target IS NULL OR target.not_in_repository = false

// Get or create the relationship and set its "mandatorily" field based on relationship data

MERGE (source)-[r:{RelationshipType.USES}]->(target)
ON CREATE
    SET r.mandatorily = rel_data.mandatorily
ON MATCH
    SET r.mandatorily = r.mandatorily OR rel_data.mandatorily

RETURN count(r) AS relationships_merged"""


def build_in_pack_relationships_query() -> str:
    return f"""// Creates IN_PACK relationships between content items and their packs.
UNWIND $data AS rel_data

// Get the pack and the content item with the specified properties
MATCH (content_item:{ContentType.BASE_NODE}{build_source_properties()})
MATCH (pack:{ContentType.PACK}{build_target_properties()})

// Get/create the relationship
MERGE (content_item)-[r:{RelationshipType.IN_PACK}]->(pack)
RETURN count(r) AS relationships_merged"""


def build_tested_by_relationships_query() -> str:
    return f"""// Creates TESTED_BY relationships between content items and their tests.
UNWIND $data AS rel_data

// Get the content item with the specified properties
MATCH (content_item:{ContentType.BASE_NODE}{build_source_properties()})

// Get or create the test playbook with the given id
MERGE (tpb:{ContentType.TEST_PLAYBOOK}{build_target_properties()})

// If created, mark "not in repository" (all repository nodes were created already)
ON CREATE
    SET tpb.not_in_repository = true

// Get/create the relationship
MERGE (content_item)-[r:{RelationshipType.TESTED_BY}]->(tpb)
RETURN count(r) AS relationships_merged
"""


def build_depends_on_relationships_query() -> str:
    return f"""
UNWIND $data AS rel_data

// Get the source and target packs
MATCH (p1:{ContentType.PACK}{{object_id: rel_data.source}}),
    (p2:{ContentType.PACK}{{object_id: rel_data.target}})

// Create the relationship, and mark as "from_metadata"
CREATE (p1)-[r:{RelationshipType.DEPENDS_ON}{{
    mandatorily: rel_data.mandatorily,
    from_metadata: true,
    is_test: false
}}]->(p2)
RETURN count(r) AS relationships_merged"""


def build_default_relationships_query(relationship: RelationshipType) -> str:
    return f"""// A default method for creating relationships
UNWIND $data AS rel_data
MATCH (source:{ContentType.BASE_NODE}{build_source_properties()})
MERGE (target:{ContentType.BASE_NODE}{build_target_properties()})
ON CREATE
    SET target.not_in_repository = true,
        target.object_id = rel_data.target,
        target.name = rel_data.target
MERGE (source)-[r:{relationship}]->(target)
RETURN count(r) AS relationships_merged"""


def create_relationships(
    tx: Transaction,
    relationships: Dict[RelationshipType, List[Dict[str, Any]]],
    timeout: Optional[int] = None,
) -> None:
    if relationships.get(RelationshipType.HAS_COMMAND):
        data = relationships.pop(RelationshipType.HAS_COMMAND)
        create_relationships_by_type(tx, RelationshipType.HAS_COMMAND, data)

    for relationship, data in relationships.items():
        create_relationships_by_type(tx, relationship, data)


def create_relationships_by_type(
    tx: Transaction,
    relationship: RelationshipType,
    data: List[Dict[str, Any]],
) -> None:
    if relationship == RelationshipType.HAS_COMMAND:
        query = build_has_command_relationships_query()
    elif relationship == RelationshipType.USES_BY_ID:
        query = build_uses_relationships_query(
            target_identifier="object_id",
        )
    elif relationship == RelationshipType.USES_BY_NAME:
        query = build_uses_relationships_query(
            target_identifier="name",
        )
    elif relationship == RelationshipType.USES_BY_CLI_NAME:
        query = build_uses_relationships_query(
            target_identifier="cli_name",
        )
    elif relationship == RelationshipType.USES_COMMAND_OR_SCRIPT:
        query = build_uses_relationships_query(
            target_identifier="object_id",
        )
    elif relationship == RelationshipType.USES_PLAYBOOK:
        query = build_uses_relationships_query(
            target_identifier="name",
        )
    elif relationship == RelationshipType.IN_PACK:
        query = build_in_pack_relationships_query()
    elif relationship == RelationshipType.TESTED_BY:
        query = build_tested_by_relationships_query()
    elif relationship == RelationshipType.DEPENDS_ON:
        query = build_depends_on_relationships_query()
    else:
        query = build_default_relationships_query(relationship)
    run_query(tx, query, data=data)
    logger.debug(f"Merged relationships of type {relationship}.")


def _match_relationships(
    tx: Transaction,
    ids_list: List[str],
    marketplace: MarketplaceVersions = None,
) -> Dict[int, Neo4jRelationshipResult]:
    """Match relationships of the given ids list.

    Args:
        tx (Transaction): The neo4j transaction.
        ids_list (List[str]): The neo4j ids list to filter by
        marketplace (MarketplaceVersions, optional): The marketplace to filter by. Defaults to None.

    Returns:
        Dict[int, Neo4jRelationshipResult]: Dictionary of neo4j ids to Neo4jRelationshipResult
    """
    marketplace_where = (
        f"AND '{marketplace}' IN node_from.marketplaces AND '{marketplace}' IN node_to.marketplaces"
        if marketplace
        else ""
    )
    query = f"""// Match relationships of the given ids list
UNWIND $ids_list AS id
MATCH (node_from) - [relationship] - (node_to)
WHERE elementId(node_from) = id
{marketplace_where}
RETURN node_from, collect(relationship) AS relationships, collect(node_to) AS nodes_to"""
    return {
        item["node_from"].element_id: Neo4jRelationshipResult(
            node_from=item.get("node_from"),
            relationships=item.get("relationships"),
            nodes_to=item.get("nodes_to"),
        )
        for item in run_query(tx, query, ids_list=list(ids_list) if ids_list else None)
    }


def get_sources_by_path(
    tx: Transaction,
    path: Path,
    relationship: RelationshipType,
    content_type: ContentType,
    depth: int,
    marketplace: MarketplaceVersions,
    mandatory_only: bool,
    include_tests: bool,
    include_deprecated: bool,
    include_hidden: bool,
) -> List[Dict[str, Any]]:
    query = f"""// Returns all paths to a given node by relationship type and depth.
MATCH (n{{path: "{path}"}})
CALL apoc.path.expandConfig(n, {{
    relationshipFilter: "<{relationship}",
    labelFilter: ">{content_type}",
    minLevel: 1,
    maxLevel: {depth},
    uniqueness: "NODE_PATH"
}})
YIELD path
WITH
    // the paths are returned in reversed order, so we fix this here:
    reverse([n IN nodes(path) | {{
        path: n.path,
        name: n.name,
        object_id: n.object_id,
        content_type: n.content_type
    }}]) AS node_paths,
    reverse(nodes(path)) AS nodes,
    reverse([r IN relationships(path) | properties(r)]) AS rels,
    length(path) AS depth
WITH
    nodes,
    nodes[0] AS source,
    apoc.coll.flatten((apoc.coll.zip(rels, node_paths[1..]))) AS path_from_source,
    CASE WHEN all(r IN rels WHERE r.mandatorily) THEN TRUE ELSE
    CASE WHEN any(r IN rels WHERE r.mandatorily IS NOT NULL) THEN FALSE END END AS mandatorily,
    depth,
    CASE WHEN any(r IN rels WHERE r.is_test) THEN TRUE ELSE FALSE END AS is_test,
    CASE WHEN any(n IN nodes WHERE n.deprecated) THEN TRUE ELSE FALSE END AS deprecated,
    CASE WHEN any(n IN nodes WHERE n.hidden) THEN TRUE ELSE FALSE END AS hidden
WHERE
    source.path IS NOT NULL
    AND all(n IN nodes WHERE "{marketplace}" IN n.marketplaces)
    {"AND NOT is_test" if not include_tests else ""}
    {"AND NOT deprecated" if not include_deprecated else ""}
    {"AND NOT hidden" if not include_hidden else ""}
    {"AND mandatorily" if mandatory_only else ""}
WITH
    source,
    min(depth) AS minDepth,
    collect({{
        path: apoc.coll.insert(
            path_from_source,
            0,
            {{
                path: source.path,
                name: source.name,
                object_id: source.object_id,
                content_type: source.content_type
            }}
        ),
        mandatorily: mandatorily,
        depth: depth,
        is_test: is_test
    }}) AS paths
RETURN
    source.object_id AS object_id,
    source.name AS name,
    source.content_type AS content_type,
    source.path AS filepath,
    TRUE AS is_source,
    paths,
    CASE WHEN any(p IN paths WHERE p.mandatorily) THEN TRUE ELSE
    CASE WHEN all(p IN paths WHERE p.mandatorily IS NOT NULL) THEN FALSE END END AS mandatorily,
    minDepth
ORDER BY content_type, object_id"""
    return run_query(tx, query).data()


def get_targets_by_path(
    tx: Transaction,
    path: Path,
    relationship: RelationshipType,
    content_type: ContentType,
    depth: int,
    marketplace: MarketplaceVersions,
    mandatory_only: bool,
    include_tests: bool,
    include_deprecated: bool,
    include_hidden: bool,
) -> List[Dict[str, Any]]:
    query = f"""// Returns all paths from a given node by relationship type and depth.
MATCH (n{{path: "{path}"}})
CALL apoc.path.expandConfig(n, {{
    relationshipFilter: "{relationship}>",
    labelFilter: ">{content_type}",
    minLevel: 1,
    maxLevel: {depth},
    uniqueness: "NODE_PATH"
}})
YIELD path
WITH
    [n IN nodes(path) | {{
        path: n.path,
        name: n.name,
        object_id: n.object_id,
        content_type: n.content_type
    }}] AS node_paths,
    nodes(path) AS nodes,
    [r IN relationships(path) | properties(r)] AS rels,
    length(path) AS depth
WITH
    nodes,
    nodes[-1] AS target,
    apoc.coll.flatten((apoc.coll.zip(node_paths[..-1], rels))) AS path_to_target,
    CASE WHEN all(r IN rels WHERE r.mandatorily) THEN TRUE ELSE
    CASE WHEN any(r IN rels WHERE r.mandatorily IS NOT NULL) THEN FALSE END END AS mandatorily,
    depth,
    CASE WHEN any(r IN rels WHERE r.is_test) THEN TRUE ELSE FALSE END AS is_test,
    CASE WHEN any(n IN nodes WHERE n.deprecated) THEN TRUE ELSE FALSE END AS deprecated,
    CASE WHEN any(n IN nodes WHERE n.hidden) THEN TRUE ELSE FALSE END AS hidden
WHERE
    target.path IS NOT NULL
    AND all(n IN nodes WHERE "{marketplace}" IN n.marketplaces)
    {"AND NOT is_test" if not include_tests else ""}
    {"AND NOT deprecated" if not include_deprecated else ""}
    {"AND NOT hidden" if not include_hidden else ""}
    {"AND mandatorily" if mandatory_only else ""}
WITH
    target,
    min(depth) AS minDepth,
    collect({{
        path: apoc.coll.insert(
            path_to_target,
            size(path_to_target),
            {{
                path: target.path,
                name: target.name,
                object_id: target.object_id,
                content_type: target.content_type
            }}
        ),
        mandatorily: mandatorily,
        depth: depth,
        is_test: is_test
    }}) AS paths
RETURN
    target.object_id AS object_id,
    target.name AS name,
    target.content_type AS content_type,
    target.path AS filepath,
    FALSE AS is_source,
    paths,
    CASE WHEN any(p IN paths WHERE p.mandatorily) THEN TRUE ELSE
    CASE WHEN all(p IN paths WHERE p.mandatorily IS NOT NULL) THEN FALSE END END AS mandatorily,
    minDepth
ORDER BY content_type, object_id"""
    return run_query(tx, query).data()
