import logging
from typing import Dict, List, Set

from neo4j import Transaction

from demisto_sdk.commands.common.constants import (REPUTATION_COMMAND_NAMES,
                                                   MarketplaceVersions)
from demisto_sdk.commands.content_graph.common import (ContentType,
                                                       Neo4jResult,
                                                       RelationshipType)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
    run_query, to_neo4j_map)

REPUTATION_COMMANDS_NODE_IDS = [
    f"{ContentType.COMMAND}:{cmd}" for cmd in REPUTATION_COMMAND_NAMES
]
IGNORED_CONTENT_ITEMS_IN_DEPENDENCY_CALC = REPUTATION_COMMANDS_NODE_IDS
IGNORED_PACKS_IN_DEPENDENCY_CALC = ["NonSupported", "Base", "ApiModules"]

MAX_DEPTH = 7

logger = logging.getLogger("demisto-sdk")


def get_all_level_packs_dependencies(
    tx: Transaction,
    marketplace: MarketplaceVersions,
    filter_list: List[int] = None,
    mandatorily: bool = False,
    **properties,
) -> List[Neo4jResult]:
    params_str = to_neo4j_map(properties)

    query = f"""
        MATCH path = (shortestPath((p1:{ContentType.PACK}{params_str})-[r:{RelationshipType.DEPENDS_ON}*..7]->(p2:{ContentType.PACK})))
        WHERE id(p1) <> id(p2) {"AND id(p1) IN $filter_list " if filter_list else ""}
        AND all(n IN nodes(path) WHERE "{marketplace}" IN n.marketplaces)
        {"AND all(r IN relationships(path) WHERE r.mandatorily = true)" if mandatorily else ""}
        RETURN p1 as pack, collect(r) as relationships, collect(p2) AS dependencies
    """
    result = run_query(tx, query, filter_list=list(filter_list) if filter_list else None)
    logger.info('Found dependencies.')
    return [Neo4jResult(node_from=item.get("pack"), nodes_to=item.get("dependencies"), relationships=item.get("relationships")) for item in result]


def create_pack_dependencies(tx: Transaction) -> None:
    fix_marketplaces_properties(tx)
    create_depends_on_relationships(tx)


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
        RETURN content_item.node_id AS excluded_content_item, dependency.node_id AS reason
    """
    result = run_query(tx, query)
    outputs: Dict[str, Set[str]] = {}
    for row in result:
        outputs.setdefault(row["excluded_content_item"], set()).add(row["reason"])
    logger.info(
        f"Removed {marketplace} from marketplaces for {len(outputs.keys())} content items."
    )


def create_depends_on_relationships(tx: Transaction) -> None:
    query = f"""
        MATCH (pack_a:{ContentType.BASE_CONTENT})<-[:{RelationshipType.IN_PACK}]-(a)
            -[r:{RelationshipType.USES}]->(b)-[:{RelationshipType.IN_PACK}]->(pack_b:{ContentType.BASE_CONTENT})
        WHERE ANY(marketplace IN pack_a.marketplaces WHERE marketplace IN pack_b.marketplaces)
        AND id(pack_a) <> id(pack_b)
        AND NOT pack_a.name IN {IGNORED_PACKS_IN_DEPENDENCY_CALC}
        AND NOT pack_b.name IN {IGNORED_PACKS_IN_DEPENDENCY_CALC}
        AND NOT b.node_id IN {IGNORED_CONTENT_ITEMS_IN_DEPENDENCY_CALC}
        WITH r, pack_a, pack_b
        MERGE (pack_a)-[dep:DEPENDS_ON]->(pack_b)
        WITH dep, r, REDUCE(
            marketplaces = [], mp IN pack_a.marketplaces |
            CASE WHEN mp IN pack_b.marketplaces THEN marketplaces + mp ELSE marketplaces END
        ) AS common_marketplaces
        SET dep.marketplaces = common_marketplaces,
            dep.mandatorily = r.mandatorily
        RETURN count(dep) AS depends_on_relationships
    """
    result = run_query(tx, query).single()
    depends_on_count: int = result["depends_on_relationships"]
    logger.info(
        f"Merged {depends_on_count} DEPENDS_ON relationships between {depends_on_count} packs."
    )
