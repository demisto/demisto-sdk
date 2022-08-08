import logging
from neo4j import Transaction
from typing import Any, Dict, List

from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import run_query


logger = logging.getLogger('demisto-sdk')


def create_relationships(
    tx: Transaction,
    relationships: Dict[Rel, List[Dict[str, Any]]],
) -> None:
    if data := relationships.pop(Rel.HAS_COMMAND):
        create_relationships_by_type(tx, Rel.HAS_COMMAND, data)

    for relationship, data in relationships.items():
        create_relationships_by_type(tx, relationship, data)


def get_has_command_relationships_query() -> str:
    return f"""
        UNWIND $data AS rel_data
        MATCH (integration:{ContentTypes.INTEGRATION}{{
            node_id: rel_data.source_node_id,
            fromversion: rel_data.source_fromversion,
            marketplaces: rel_data.source_marketplaces
        }})
        MERGE (cmd:{ContentTypes.COMMAND}{{
            id: rel_data.target
        }})
        ON CREATE
            SET cmd:{ContentTypes.BASE_CONTENT},
                cmd.node_id = "{ContentTypes.COMMAND}:" + rel_data.target,
                cmd.marketplaces = rel_data.source_marketplaces
        ON MATCH
            SET cmd.marketplaces = REDUCE(
                marketplaces = cmd.marketplaces, mp IN rel_data.source_marketplaces |
                CASE WHEN NOT mp IN cmd.marketplaces THEN marketplaces + mp ELSE marketplaces END
            )
        MERGE (integration)-[r:{Rel.HAS_COMMAND}{{deprecated: rel_data.deprecated}}]->(cmd)

        RETURN count(r) AS relationships_created
    """


def get_uses_relationships_query(target_type: ContentTypes) -> str:
    """
    Args:
        target_type (ContentTypes): If node_id is known, target type is BaseContent.
            Otherwise, a more specific ContentType, E.g., CommandOrScript.

    This query searches for a content item by its type, ID and marketplaces,
    as well as the dependency by its ID, type and whether it exists in one of the content item's marketplaces.
    If both found, we create a USES relationship between them.
    """
    if target_type == ContentTypes.BASE_CONTENT:
        target_property = 'node_id'
    else:
        target_property = 'id'

    query = f"""
        UNWIND $data AS rel_data
        MATCH (content_item:{ContentTypes.BASE_CONTENT}{{
            node_id: rel_data.source_node_id,
            fromversion: rel_data.source_fromversion,
            marketplaces: rel_data.source_marketplaces
        }})
        MATCH (dependency:{target_type}{{
            {target_property}: rel_data.target
        }})
        WHERE ANY(
            marketplace IN dependency.marketplaces
            WHERE marketplace IN rel_data.source_marketplaces
        )
        MERGE (content_item)-[r:{Rel.USES}]->(dependency)
        ON CREATE
            SET r.mandatorily = rel_data.mandatorily
        ON MATCH
            SET r.mandatorily = r.mandatorily OR rel_data.mandatorily
        
        RETURN count(r) AS relationships_created
    """
    return query


def get_in_pack_relationships_query() -> str:
    return f"""
        UNWIND $data AS rel_data
        MATCH (source:{ContentTypes.BASE_CONTENT}{{node_id: rel_data.source_node_id}})
        MATCH (target:{ContentTypes.PACK}{{node_id: rel_data.target}})
        MERGE (source)-[r:{Rel.IN_PACK}]->(target)
            RETURN count(r) AS relationships_created
    """


def create_relationships_by_type(
    tx: Transaction,
    relationship: Rel,
    data: List[Dict[str, Any]],
) -> None:
    if relationship == Rel.HAS_COMMAND:
        query = get_has_command_relationships_query()
    elif relationship == Rel.USES:
        query = get_uses_relationships_query(target_type=ContentTypes.BASE_CONTENT)
    elif relationship == Rel.USES_COMMAND_OR_SCRIPT:
        query = get_uses_relationships_query(target_type=ContentTypes.COMMAND_OR_SCRIPT)
    elif relationship == Rel.IN_PACK:
        query = get_in_pack_relationships_query()
    else:
        # default query
        query = f"""
            UNWIND $data AS rel_data
            MATCH (source:{ContentTypes.BASE_CONTENT}{{node_id: rel_data.source_node_id}})
            MATCH (target:{ContentTypes.BASE_CONTENT}{{node_id: rel_data.target}})
            MERGE (source)-[r:{relationship}]->(target)
            RETURN count(r) AS relationships_created
        """

    result = tx.run(query, data=data)
    result = run_query(tx, query, data=data).single()
    relationships_count: int = result['relationships_created']
    logger.info(f'Created {relationships_count} relationships of type {relationship}.')
