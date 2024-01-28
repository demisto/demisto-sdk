import os
from pathlib import Path
from typing import Dict, List

from neo4j import Transaction

from demisto_sdk.commands.common.constants import (
    DEPRECATED_CONTENT_PACK,
    GENERIC_COMMANDS_NAMES,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import (
    ContentType,
    Neo4jRelationshipResult,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
    is_target_available,
    run_query,
    to_neo4j_map,
)

json = JSON_Handler()
IGNORED_PACKS_IN_DEPENDENCY_CALC = ["NonSupported", "ApiModules"]

MAX_DEPTH = 5


def get_all_level_packs_relationships(
    tx: Transaction,
    relationship_type: RelationshipType,
    ids_list: List[str],
    marketplace: MarketplaceVersions,
    mandatorily: bool = False,
    **properties,
) -> Dict[int, Neo4jRelationshipResult]:
    params_str = to_neo4j_map(properties)

    if relationship_type == RelationshipType.DEPENDS_ON:
        query = f"""
            UNWIND $ids_list AS node_id
            MATCH path = shortestPath((p1:{ContentType.PACK}{params_str})-[r:{relationship_type}*..{MAX_DEPTH}]->(p2:{ContentType.PACK}))
            WHERE elementId(p1) = node_id AND elementId(p1) <> elementId(p2)
            AND all(n IN nodes(path) WHERE "{marketplace}" IN n.marketplaces)
            AND all(r IN relationships(path) WHERE NOT r.is_test {"AND r.mandatorily = true)" if mandatorily else ""}
            RETURN node_id, collect(r) as relationships, collect(p2) AS nodes_to
        """
    if relationship_type == RelationshipType.IMPORTS:
        # search all the content items that import the 'node_from' content item
        query = f"""UNWIND $ids_list AS node_id
            MATCH path=shortestPath((node_from) <- [relationship:{relationship_type}*..{MAX_DEPTH}] - (node_to))
            WHERE elementId(node_from) = node_id and node_from <> node_to
            return node_id, node_from, collect(relationship) AS relationships,
            collect(node_to) AS nodes_to
        """

    result = run_query(tx, query, ids_list=list(ids_list))
    logger.debug("Found dependencies.")
    return {
        item.get("node_id"): Neo4jRelationshipResult(
            node_from=item.get("node_from"),
            nodes_to=item.get("nodes_to"),
            relationships=item.get("relationships"),
        )
        for item in result
    }


def create_pack_dependencies(tx: Transaction) -> dict:
    remove_existing_depends_on_relationships(tx)
    update_uses_for_integration_commands(tx)
    delete_deprecatedcontent_relationship(tx)  # TODO decide what to do with this
    depends_on_data = create_depends_on_relationships(tx)
    return depends_on_data


def delete_deprecatedcontent_relationship(tx: Transaction) -> None:
    """
    This will delete any USES relationship between a content item and a content item in the deprecated content pack.
    At the moment, we do not want to consider this pack in the dependency calculation.
    """
    query = f"""// Deletes USES relationships to content items under DeprecatedContent pack.
MATCH (source) - [r:{RelationshipType.USES}] -> (target) - [:{RelationshipType.IN_PACK}] ->
(:{ContentType.PACK}{{object_id: "{DEPRECATED_CONTENT_PACK}"}})
DELETE r
RETURN source.node_id AS source, target.node_id AS target"""
    run_query(tx, query)


def remove_existing_depends_on_relationships(tx: Transaction) -> None:
    query = f"""// Removes all existing DEPENDS_ON relationships before recalculation
MATCH ()-[r:{RelationshipType.DEPENDS_ON}]->()
WHERE r.from_metadata = false
DELETE r"""
    run_query(tx, query)


def update_uses_for_integration_commands(tx: Transaction) -> None:
    """This query creates a relationships between content items and integrations, based on the commands they use.
    If a content item uses a command which is in an integration, we create a relationship between the content item and the integration.
    The mandatorily property is calculated as follows:
        - If there is only one integration that implements the command, the mandatorily property is the same as the command's mandatorily property.
          Otherwise, the mandatorily property is false.
        - If there is already a relationship between the content item and the integration,
          the mandatorily property is the OR of the existing and the new mandatorily property.

    Args:
        tx (Transaction): _description_
    """
    query = f"""// Creates USES relationships between content items and integrations, based on the commands they use.
MATCH (content_item:{ContentType.BASE_NODE})
    -[r:{RelationshipType.USES}]->
        (command:{ContentType.COMMAND})<-[rcmd:{RelationshipType.HAS_COMMAND}]
        -(integration:{ContentType.INTEGRATION})
WHERE {is_target_available("content_item", "integration")}
AND NOT command.object_id IN {list(GENERIC_COMMANDS_NAMES)}
WITH command, count(DISTINCT rcmd) as command_count

MATCH (content_item:{ContentType.BASE_NODE})
    -[r:{RelationshipType.USES}]->
        (command)<-[rcmd:{RelationshipType.HAS_COMMAND}]
        -(integration:{ContentType.INTEGRATION})
WHERE {is_target_available("content_item", "integration")}
AND NOT command.object_id IN {list(GENERIC_COMMANDS_NAMES)}

MERGE (content_item)-[u:{RelationshipType.USES}]->(integration)
ON CREATE
    SET u.mandatorily = CASE WHEN command_count = 1 THEN r.mandatorily ELSE false END
ON MATCH
    SET u.mandatorily = u.mandatorily OR (CASE WHEN command_count = 1 THEN r.mandatorily ELSE false END)
RETURN
    content_item.node_id AS content_item,
    r.mandatorily AS is_cmd_mandatory,
    collect(integration.object_id) AS integrations,
    u.mandatorily AS is_integ_mandatory,
    command.name AS command"""
    run_query(tx, query)


def create_depends_on_relationships(tx: Transaction) -> dict:
    query = f"""// Creates DEPENDS_ON relationships
MATCH (pack_a:{ContentType.BASE_NODE})<-[:{RelationshipType.IN_PACK}]-(a)
    -[r:{RelationshipType.USES}]->(b)-[:{RelationshipType.IN_PACK}]->(pack_b:{ContentType.BASE_NODE})
WHERE ANY(marketplace IN pack_a.marketplaces WHERE marketplace IN pack_b.marketplaces)
AND elementId(pack_a) <> elementId(pack_b)
AND NOT pack_b.object_id IN pack_a.excluded_dependencies
AND NOT pack_a.name IN {IGNORED_PACKS_IN_DEPENDENCY_CALC}
AND NOT pack_b.name IN {IGNORED_PACKS_IN_DEPENDENCY_CALC}
WITH pack_a, a, r, b, pack_b
MERGE (pack_a)-[dep:{RelationshipType.DEPENDS_ON}]->(pack_b)
ON CREATE
    SET dep.is_test = a.is_test,
        dep.from_metadata = false,
        dep.mandatorily = r.mandatorily
ON MATCH
    SET dep.is_test = dep.is_test AND a.is_test,
        dep.mandatorily = CASE WHEN dep.from_metadata THEN dep.mandatorily
                ELSE r.mandatorily OR dep.mandatorily END
WITH
    pack_a.object_id AS pack_a,
    pack_b.object_id AS pack_b,
    collect({{
        source: a.node_id,
        target: b.node_id,
        mandatorily: r.mandatorily,
        is_test: a.is_test
    }}) AS reasons
RETURN
    pack_a, pack_b, reasons"""
    result = run_query(tx, query)
    outputs: Dict[str, Dict[str, list]] = {}
    for row in result:
        pack_a = row["pack_a"]
        pack_b = row["pack_b"]
        outputs.setdefault(pack_a, {}).setdefault(pack_b, []).extend(row["reasons"])

    if (artifacts_folder := os.getenv("ARTIFACTS_FOLDER")) and Path(
        artifacts_folder
    ).exists():
        with open(f"{artifacts_folder}/depends_on.json", "w") as fp:
            json.dump(outputs, fp, indent=4)
    return outputs
