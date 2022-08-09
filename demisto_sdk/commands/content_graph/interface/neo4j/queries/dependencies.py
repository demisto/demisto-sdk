import logging
from neo4j import Transaction

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import run_query


IGNORED_PACKS_IN_DEPENDENCY_CALC = ['NonSupported', 'Base', 'ApiModules']


logger = logging.getLogger('demisto-sdk')


def create_pack_dependencies(tx: Transaction) -> None:
    fix_marketplaces_properties(tx)
    create_depends_on_relationships(tx)


def fix_marketplaces_properties(tx: Transaction) -> None:
    for marketplace in MarketplaceVersions:
        update_marketplaces_property(tx, marketplace.value)


def update_marketplaces_property(tx: Transaction, marketplace: str) -> None:
    """
    In this query, we find all content items that are currently considered in a given marketplace,
    but uses a dependency that is not in this marketplace.
    To make sure the dependency is not in this marketplace, we make sure there is no alternative with
    the same content type and id as the dependency which is in the marketplace.

    If such dependencies were found, we drop the content item from the marketplace.
    """
    # todo: USES{mandatorily?}
    # ignore IGNORED_PACKS_IN_DEPENDENCY_CALC?
    query = f"""
        MATCH (content_item:{ContentTypes.BASE_CONTENT})
                -[r:{Rel.USES}*{{mandatorily: true}}]->
                    (dependency:{ContentTypes.BASE_CONTENT})
        WHERE
            "{marketplace}" IN content_item.marketplaces
        AND
            NOT "{marketplace}" IN dependency.marketplaces
        OPTIONAL MATCH (alternative_dependency:{ContentTypes.BASE_CONTENT}{{node_id: dependency.node_id}})
        WHERE
            "{marketplace}" IN alternative_dependency.marketplaces
        WITH content_item, alternative_dependency
        WHERE alternative_dependency IS NULL
        SET content_item.marketplaces = REDUCE(
            marketplaces = [], mp IN content_item.marketplaces |
            CASE WHEN mp <> "{marketplace}" THEN marketplaces + mp ELSE marketplaces END
        )
        RETURN count(content_item) AS updated_marketplaces_count  // fix count
    """
    result = run_query(tx, query).single()
    updated_marketplaces_count: int = result['updated_marketplaces_count']
    logger.info(f'Removed {marketplace} from marketplaces for {updated_marketplaces_count} content items.')


def create_depends_on_relationships(tx: Transaction) -> None:
    query = f"""
        MATCH (pack_a:{ContentTypes.BASE_CONTENT})<-[:{Rel.IN_PACK}]-(a)
            -[r:{Rel.USES}]->(b)-[:{Rel.IN_PACK}]->(pack_b:{ContentTypes.BASE_CONTENT})
        WHERE ANY(marketplace IN pack_a.marketplaces WHERE marketplace IN pack_b.marketplaces)
        AND pack_a.id <> pack_b.id
        AND NOT pack_a.id IN {IGNORED_PACKS_IN_DEPENDENCY_CALC}
        AND NOT pack_b.id IN {IGNORED_PACKS_IN_DEPENDENCY_CALC}
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
    depends_on_count: int = result['depends_on_relationships']
    logger.info(f'Merged {depends_on_count} DEPENDS_ON relationships between {depends_on_count} packs.')
