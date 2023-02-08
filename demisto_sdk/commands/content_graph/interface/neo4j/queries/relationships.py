import logging
from typing import Any, Dict, List

from neo4j import Transaction

from demisto_sdk.commands.common.constants import MarketplaceVersions
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
    target_type: ContentType = ContentType.BASE_CONTENT,
    target_identifier: str = "object_id",
    with_target_type: bool = True,
) -> str:
    return f"""// Creates USES relationships between parsed nodes.
// Note: if a target node is created, it means the node does not exist in the repository.
UNWIND $data AS rel_data

// Get all content items with the specified properties
MATCH (source:{ContentType.BASE_CONTENT}{build_source_properties()})

// Get or create the targets with the given properties
MERGE (target:{target_type}{
    build_target_properties(identifier=target_identifier, with_content_type=with_target_type)
})

// If created, mark "not in repository" (all repository nodes were created already)
ON CREATE
    SET target.not_in_repository = true

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
MATCH (content_item:{ContentType.BASE_CONTENT}{build_source_properties()})
MATCH (pack:{ContentType.PACK}{build_target_properties()})

// Get/create the relationship
MERGE (content_item)-[r:{RelationshipType.IN_PACK}]->(pack)
RETURN count(r) AS relationships_merged"""


def build_tested_by_relationships_query() -> str:
    return f"""// Creates TESTED_BY relationships between content items and their tests.
UNWIND $data AS rel_data

// Get the content item with the specified properties
MATCH (content_item:{ContentType.BASE_CONTENT}{build_source_properties()})

// Get or create the test playbook with the given id
MERGE (tpb:{ContentType.TEST_PLAYBOOK}{build_target_properties(with_content_type=True)})

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
    from_metadata: true
}}]->(p2)
RETURN count(r) AS relationships_merged"""


def build_default_relationships_query(relationship: RelationshipType) -> str:
    return f"""// A default method for creating relationships
UNWIND $data AS rel_data
MATCH (source:{ContentType.BASE_CONTENT}{build_source_properties()})
MERGE (target:{ContentType.BASE_CONTENT}{build_target_properties()})
ON CREATE
    SET target.not_in_repository = true
MERGE (source)-[r:{relationship}]->(target)
RETURN count(r) AS relationships_merged"""


logger = logging.getLogger("demisto-sdk")


def create_relationships(
    tx: Transaction,
    relationships: Dict[RelationshipType, List[Dict[str, Any]]],
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
    elif relationship == RelationshipType.USES_COMMAND_OR_SCRIPT:
        query = build_uses_relationships_query(
            target_type=ContentType.COMMAND_OR_SCRIPT,
            target_identifier="object_id",
            with_target_type=False,
        )
    elif relationship == RelationshipType.USES_PLAYBOOK:
        query = build_uses_relationships_query(
            target_type=ContentType.PLAYBOOK,
            target_identifier="name",
            with_target_type=False,
        )
    elif relationship == RelationshipType.IN_PACK:
        query = build_in_pack_relationships_query()
    elif relationship == RelationshipType.TESTED_BY:
        query = build_tested_by_relationships_query()
    elif relationship == RelationshipType.DEPENDS_ON:
        query = build_depends_on_relationships_query()
    else:
        query = build_default_relationships_query(relationship)

    result = run_query(tx, query, data=data).single()
    merged_relationships_count: int = result["relationships_merged"]
    logger.debug(
        f"Merged {merged_relationships_count} relationships of type {relationship}."
    )


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
WHERE id(node_from) = id
{marketplace_where}
RETURN node_from, collect(relationship) AS relationships, collect(node_to) AS nodes_to"""
    return {
        int(item["node_from"].id): Neo4jRelationshipResult(
            node_from=item.get("node_from"),
            relationships=item.get("relationships"),
            nodes_to=item.get("nodes_to"),
        )
        for item in run_query(tx, query, ids_list=list(ids_list) if ids_list else None)
    }
