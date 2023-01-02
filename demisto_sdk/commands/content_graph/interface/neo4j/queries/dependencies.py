import json
import logging
import os
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
        {"AND all(r IN relationships(path) WHERE r.mandatorily = true)" if mandatorily else ""}
        RETURN pack_id, collect(r) as relationships, collect(p2) AS dependencies
    """
    result = run_query(tx, query, ids_list=list(ids_list))
    logger.info("Found dependencies.")
    return {
        int(item.get("pack_id")): Neo4jRelationshipResult(
            nodes_to=item.get("dependencies"), relationships=item.get("relationships")
        )
        for item in result
    }


def create_pack_dependencies(tx: Transaction) -> None:
    remove_existing_depends_on_relationships(tx)
    fix_marketplaces_properties(tx)
    update_uses_for_integration_commands(tx)
    delete_deprecatedcontent_relationship(tx)  # TODO decide what to do with this
    create_depends_on_relationships(tx)


def delete_deprecatedcontent_relationship(tx: Transaction) -> None:
    """
    This will delete any USES relationship between a content item and a content item in the deprecated content pack.
    At the moment, we do not want to consider this pack in the dependency calculation.
    """
    query = f"""
        MATCH (source) - [r:{RelationshipType.USES}] -> (target) - [:{RelationshipType.IN_PACK}] ->
        (:{ContentType.PACK}{{object_id: "{DEPRECATED_CONTENT_PACK}"}})
        DELETE r
        RETURN source.node_id AS source, target.node_id AS target, type(r) AS r
    """
    result = run_query(tx, query).data()
    for row in result:
        source = row["source"]
        target = row["target"]
        relationship = row["r"]
        logger.debug(
            f"Deleted relationship {relationship} between {source} and {target}"
        )


def remove_existing_depends_on_relationships(tx: Transaction) -> None:
    query = f"""
        MATCH ()-[r:{RelationshipType.DEPENDS_ON}]->()
        DELETE r
    """
    run_query(tx, query)


def fix_marketplaces_properties(tx: Transaction) -> None:
    """
    Currently the content repo does not hold valid marketplaces attributes, so we fix it with the graph.

    Args:
        tx (Transaction): neo4j transaction
    """
    inherit_content_items_marketplaces_property_from_packs(tx)
    for marketplace in MarketplaceVersions:
        update_marketplaces_property(tx, marketplace.value)


def inherit_content_items_marketplaces_property_from_packs(tx: Transaction) -> None:
    query = f"""
        MATCH (content_item:{ContentType.BASE_CONTENT})-[:{RelationshipType.IN_PACK}]->(pack)
        WHERE content_item.marketplaces = []
        WITH content_item, pack
        SET content_item.marketplaces = pack.marketplaces
        RETURN count(content_item) AS updated
    """
    result = run_query(tx, query).single()
    updated_count: int = result["updated"]
    logger.info(f"Updated marketplaces properties of {updated_count} content items.")


def update_marketplaces_property(tx: Transaction, marketplace: str) -> None:
    """
    In this query, we find all content items that are currently considered in a given marketplace,
    but uses a dependency that is not in this marketplace.
    To make sure the dependency is not in this marketplace, we make sure there is no alternative with
    the same content type and id as the dependency which is in the marketplace.

    In addition, we will not handle cases which the dependency is a generic command, as we assume it exists.

    If such dependencies were found, we drop the content item from the marketplace.
    """
    query = f"""
        MATCH (content_item:{ContentType.BASE_CONTENT})
                -[r:{RelationshipType.USES}*..{MAX_DEPTH}{{mandatorily: true}}]->
                    (dependency:{ContentType.BASE_CONTENT})
        WHERE
            "{marketplace}" IN content_item.marketplaces
        AND
            NOT "{marketplace}" IN dependency.marketplaces
        AND
            NOT dependency.object_id IN {list(GENERIC_COMMANDS_NAMES)}
        OPTIONAL MATCH (alternative_dependency:{ContentType.BASE_CONTENT}{{node_id: dependency.node_id}})
        WHERE
            "{marketplace}" IN alternative_dependency.marketplaces
        WITH content_item, dependency, alternative_dependency
        WHERE alternative_dependency IS NULL
        SET content_item.marketplaces = REDUCE(
            marketplaces = [], mp IN content_item.marketplaces |
            CASE WHEN mp <> "{marketplace}" THEN marketplaces + mp ELSE marketplaces END
        )
        RETURN content_item.node_id AS excluded_content_item, dependency.content_type + ":" + dependency.object_id AS reason
    """
    result = run_query(tx, query)
    outputs: Dict[str, List[str]] = {}
    for row in result:
        outputs.setdefault(row["excluded_content_item"], list()).append(row["reason"])
    logger.info(
        f"Removed {marketplace} from marketplaces for {len(outputs.keys())} content items."
    )
    logger.debug(f"Excluded content items: {dict(sorted(outputs.items()))}")
    if artifacts_folder := os.getenv("ARTIFACTS_FOLDER"):
        with open(
            f"{artifacts_folder}/removed_from_marketplace-{marketplace}.json", "w"
        ) as fp:
            json.dump(dict(sorted(outputs.items())), fp, indent=4)


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
    query = f"""
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
        command.name AS command

    """
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
    query = f"""
        MATCH (pack_a:{ContentType.BASE_CONTENT})<-[:{RelationshipType.IN_PACK}]-(a)
            -[r:{RelationshipType.USES}]->(b)-[:{RelationshipType.IN_PACK}]->(pack_b:{ContentType.BASE_CONTENT})
        WHERE ANY(marketplace IN pack_a.marketplaces WHERE marketplace IN pack_b.marketplaces)
        AND id(pack_a) <> id(pack_b)
        AND NOT pack_a.name IN {IGNORED_PACKS_IN_DEPENDENCY_CALC}
        AND NOT pack_b.name IN {IGNORED_PACKS_IN_DEPENDENCY_CALC}
        AND a.is_test <> true
        AND b.is_test <> true
        WITH pack_a, a, r, b, pack_b
        MERGE (pack_a)-[dep:DEPENDS_ON]->(pack_b)
        WITH dep, pack_a, a, r, b, pack_b, REDUCE(
            marketplaces = [], mp IN pack_a.marketplaces |
            CASE WHEN mp IN pack_b.marketplaces THEN marketplaces + mp ELSE marketplaces END
        ) AS common_marketplaces
        SET dep.marketplaces = common_marketplaces,
            dep.mandatorily = r.mandatorily OR dep.mandatorily
        WITH
            pack_a.object_id AS pack_a,
            pack_b.object_id AS pack_b,
            collect({{
                source: a.node_id,
                target: b.node_id,
                mandatorily: r.mandatorily
            }}) AS reasons
        RETURN
            pack_a, pack_b, reasons
    """
    result = run_query(tx, query)
    outputs: Dict[str, Dict[str, list]] = {}
    for row in result:
        pack_a = row["pack_a"]
        pack_b = row["pack_b"]
        outputs.setdefault(pack_a, {}).setdefault(pack_b, []).extend(row["reasons"])
    for pack_a, pack_b in outputs.items():
        for pack_b, reasons in pack_b.items():
            logger.debug(
                f"Created DEPENDS_ON relationship between {pack_a} and {pack_b}"
            )
            for reason in reasons:
                logger.debug(
                    f"Reason: {reason.get('source')} -> {reason.get('target')} (mandatorily: {reason.get('mandatorily')})"
                )

    if artifacts_folder := os.getenv("ARTIFACTS_FOLDER"):
        with open(f"{artifacts_folder}/depends_on.json", "w") as fp:
            json.dump(outputs, fp, indent=4)
