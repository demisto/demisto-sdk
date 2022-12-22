import logging
from typing import Any, Dict, List, Set

from neo4j import Transaction

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType, Neo4jRelationshipResult, RelationshipType
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (is_target_available, run_query,
                                                                               to_neo4j_map)

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
    create_depends_on_relationships(tx)


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
    outputs: Dict[str, Set[str]] = {}
    for row in result:
        outputs.setdefault(row["excluded_content_item"], set()).add(row["reason"])
    logger.info(f"Removed {marketplace} from marketplaces for {len(outputs.keys())} content items.")
    logger.debug(f"Excluded content items: {dict(sorted(outputs.items()))}")


def update_uses_for_integration_commands(tx: Transaction) -> None:
    query = f"""
    MATCH (content_item:{ContentType.BASE_CONTENT})-[r:{RelationshipType.USES}]->(command:{ContentType.COMMAND})
    MATCH (command)<-[rcmd:{RelationshipType.HAS_COMMAND}]-(integration:{ContentType.INTEGRATION})
    WHERE {is_target_available("content_item", "integration")}

    WITH count(rcmd) as command_count, content_item, r, integration
    MERGE (content_item)-[u:USES]->(integration)
    SET u.mandatorily = u.mandatorily AND (CASE WHEN command_count = 1 THEN true ELSE false END)
    RETURN count(u) as uses_relationships
    """
    result = run_query(tx, query).single()
    uses_count = result["uses_relationships"]
    logger.info(f"Merged {uses_count} USES relationships based on commands.")


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
                source: a.object_id,
                target: b.object_id,
                mandatorily: r.mandatorily
            }}) AS reasons
        RETURN
            pack_a, pack_b, reasons
    """
    result = run_query(tx, query)
    outputs: Dict[str, List[Dict[str, Any]]] = {}
    for row in result:
        dep = row["pack_a"] + " depends on " + row["pack_b"]
        outputs[dep] = row["reasons"]
    outputs = dict(sorted(outputs.items()))
    for dep, reasons in outputs.items():
        for idx, reason in enumerate(reasons, 1):
            reasons_str = f"{idx}. " + reason["source"] + " uses " + reason["target"]
            reasons_str += " mandatorily.\n" if reason["mandatorily"] else " optionally.\n"
            logger.debug(f"{dep} because:\n{reasons_str}---------\n")
