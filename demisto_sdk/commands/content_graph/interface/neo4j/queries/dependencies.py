import json
import logging
import os
from pathlib import Path
from typing import Dict, List

from neo4j import Transaction

from demisto_sdk.commands.common.constants import (
    DEPRECATED_CONTENT_PACK,
    GENERIC_COMMANDS_NAMES,
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
    to_neo4j_map,
)

IGNORED_PACKS_IN_DEPENDENCY_CALC = ["NonSupported", "Base", "ApiModules"]

MAX_DEPTH = 5

logger = logging.getLogger("demisto-sdk")


def get_all_level_packs_dependencies(
    tx: Transaction,
    ids_list: List[int],
    marketplace: MarketplaceVersions,
    mandatorily: bool = False,
    **properties,
) -> Dict[int, Neo4jRelationshipResult]:
    params_str = to_neo4j_map(properties)

    query = f"""
        UNWIND $ids_list AS pack_id
        MATCH path = (shortestPath((p1:{ContentType.PACK}{params_str})-[r:{RelationshipType.DEPENDS_ON}*..{MAX_DEPTH}]->(p2:{ContentType.PACK})))
        WHERE id(p1) = pack_id AND id(p1) <> id(p2)
        AND all(n IN nodes(path) WHERE "{marketplace}" IN n.marketplaces)
        AND all(r IN relationships(path) WHERE NOT r.is_test {"AND r.mandatorily = true)" if mandatorily else ""}
        RETURN pack_id, collect(r) as relationships, collect(p2) AS dependencies
    """
    result = run_query(tx, query, ids_list=list(ids_list))
    logger.debug("Found dependencies.")
    return {
        int(item.get("pack_id")): Neo4jRelationshipResult(
            node_from=item.get("node_from"),
            nodes_to=item.get("dependencies"),
            relationships=item.get("relationships"),
        )
        for item in result
    }


def create_pack_dependencies(tx: Transaction) -> None:
    remove_existing_depends_on_relationships(tx)
    update_uses_for_integration_commands(tx)
    delete_deprecatedcontent_relationship(tx)  # TODO decide what to do with this
    create_depends_on_relationships(tx)


def delete_deprecatedcontent_relationship(tx: Transaction) -> None:
    """
    This will delete any USES relationship between a content item and a content item in the deprecated content pack.
    At the moment, we do not want to consider this pack in the dependency calculation.
    """
    query = f"""// Deletes USES relationships to content items under DeprecatedContent pack.
MATCH (source) - [r:{RelationshipType.USES}] -> (target) - [:{RelationshipType.IN_PACK}] ->
(:{ContentType.PACK}{{object_id: "{DEPRECATED_CONTENT_PACK}"}})
DELETE r
RETURN source.node_id AS source, target.node_id AS target, type(r) AS r"""
    result = run_query(tx, query).data()
    for row in result:
        source = row["source"]
        target = row["target"]
        relationship = row["r"]
        logger.debug(
            f"Deleted relationship {relationship} between {source} and {target}"
        )


def remove_existing_depends_on_relationships(tx: Transaction) -> None:
    query = f"""// Removes all existing DEPENDS_ON relationships before recalculation
MATCH ()-[r:{RelationshipType.DEPENDS_ON}]->()
WHERE r.from_metadata IS NULL
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
MATCH (content_item:{ContentType.BASE_CONTENT})
    -[r:{RelationshipType.USES}]->
        (command:{ContentType.COMMAND})<-[rcmd:{RelationshipType.HAS_COMMAND}]
        -(integration:{ContentType.INTEGRATION})
WHERE {is_target_available("content_item", "integration")}
AND NOT command.object_id IN {list(GENERIC_COMMANDS_NAMES)}
WITH command, count(DISTINCT rcmd) as command_count

MATCH (content_item:{ContentType.BASE_CONTENT})
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
    result = run_query(tx, query)
    for row in result:
        content_item = row["content_item"]
        command = row["command"]
        is_cmd_mandatory = "mandatory" if row["is_cmd_mandatory"] else "optional"
        integrations = row["integrations"]
        is_integ_mandatory = "mandatory" if row["is_integ_mandatory"] else "optional"
        msg = (
            f"{content_item} uses command {command} ({is_cmd_mandatory}), "
            f"new {is_integ_mandatory} relationships to integrations: {integrations}"
        )
        logger.debug(msg)


def create_depends_on_relationships(tx: Transaction) -> None:
    query = f"""// Creates DEPENDS_ON relationships
MATCH (pack_a:{ContentType.BASE_CONTENT})<-[:{RelationshipType.IN_PACK}]-(a)
    -[r:{RelationshipType.USES}]->(b)-[:{RelationshipType.IN_PACK}]->(pack_b:{ContentType.BASE_CONTENT})
WHERE ANY(marketplace IN pack_a.marketplaces WHERE marketplace IN pack_b.marketplaces)
AND id(pack_a) <> id(pack_b)
AND NOT pack_b.object_id IN pack_a.excluded_dependencies
AND NOT pack_a.name IN {IGNORED_PACKS_IN_DEPENDENCY_CALC}
AND NOT pack_b.name IN {IGNORED_PACKS_IN_DEPENDENCY_CALC}
WITH pack_a, a, r, b, pack_b
MERGE (pack_a)-[dep:{RelationshipType.DEPENDS_ON}]->(pack_b)
ON CREATE
    SET dep.is_test = a.is_test
ON MATCH
    SET dep.is_test = dep.is_test AND a.is_test

WITH dep, pack_a, a, r, b, pack_b
SET dep.mandatorily = CASE WHEN dep.from_metadata THEN dep.mandatorily
                ELSE r.mandatorily OR dep.mandatorily END
WITH
    pack_a.object_id AS pack_a,
    pack_b.object_id AS pack_b,
    collect({{
        source: a.node_id,
        target: b.node_id,
        mandatorily: r.mandatorily
    }}) AS reasons
RETURN
    pack_a, pack_b, reasons"""
    result = run_query(tx, query)
    outputs: Dict[str, Dict[str, list]] = {}
    for row in result:
        pack_a = row["pack_a"]
        pack_b = row["pack_b"]
        outputs.setdefault(pack_a, {}).setdefault(pack_b, []).extend(row["reasons"])
    for pack_a, pack_b in outputs.items():
        for pack_b, reasons in pack_b.items():
            msg = f"Created a DEPENDS_ON relationship between {pack_a} and {pack_b}. Reasons:\n"
            for idx, reason in enumerate(reasons, 1):
                msg += f"{idx}. [{reason.get('source')}] -> [{reason.get('target')}] (mandatorily: {reason.get('mandatorily')})\n"
            logger.debug(msg)

    if (artifacts_folder := os.getenv("ARTIFACTS_FOLDER")) and Path(
        artifacts_folder
    ).exists():
        with open(f"{artifacts_folder}/depends_on.json", "w") as fp:
            json.dump(outputs, fp, indent=4)
