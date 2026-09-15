"""Cypher queries severing every relationship crossing a managed pack boundary; IN_PACK, HAS_COMMAND and IMPORTS are kept."""

from typing import List, Set, Tuple

from neo4j import Transaction

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
    are_in_the_same_split_pack_family,
    is_managed_or_derived,
    run_query,
)

# Keep-list, not delete-list: an unknown relationship type is severed by default.
PRESERVED_RELATIONSHIP_TYPES: Tuple[RelationshipType, ...] = (
    RelationshipType.IN_PACK,
    RelationshipType.HAS_COMMAND,
    RelationshipType.IMPORTS,
)

# A node belongs to a pack by being it (zero hops) or via IN_PACK (one hop).
_IN_PACK_HOPS = f"-[:{RelationshipType.IN_PACK}*0..1]->"


def _belongs_to_pack(node: str, pack: str) -> str:
    """Builds a pattern matching ``node`` against a pack it belongs to."""
    return f"({node}){_IN_PACK_HOPS}({pack})"


def _has_a_pack(node: str) -> str:
    """Cypher predicate: the node belongs to some pack (commands, connectors and stubs do not)."""
    return f"EXISTS {{ {_belongs_to_pack(node, f'_any_pack:{ContentType.PACK}')} }}"


def _share_a_pack(node_a: str, node_b: str) -> str:
    """Cypher predicate quantified over all packs: sever only when no pack contains both endpoints."""
    shared_pack = f"_shared_pack:{ContentType.PACK}"
    return (
        f"EXISTS {{ ({node_a}){_IN_PACK_HOPS}({shared_pack})"
        f"<-[:{RelationshipType.IN_PACK}*0..1]-({node_b}) }}"
    )


def _sever_managed_pack_dependencies(tx: Transaction) -> Set[Tuple[str, str]]:
    """Delete pack-level DEPENDS_ON where either endpoint is managed, derived or a twin; returns the deleted pairs."""
    query = f"""// Severs pack dependencies involving managed, derived or twin packs
MATCH (pack_a:{ContentType.PACK})-[r:{RelationshipType.DEPENDS_ON}]->(pack_b:{ContentType.PACK})
WHERE {is_managed_or_derived("pack_a")}
OR {is_managed_or_derived("pack_b")}
OR {are_in_the_same_split_pack_family("pack_a", "pack_b")}
WITH r, pack_a.object_id AS source, pack_b.object_id AS target
DELETE r
RETURN source, target"""
    severed = {(row["source"], row["target"]) for row in run_query(tx, query)}
    for source, target in sorted(severed):
        logger.debug(f"Severed pack dependency {source} -> {target}.")
    return severed


def _sever_cross_pack_content_relationships(tx: Transaction) -> int:
    """Delete non-structural relationships crossing a managed pack boundary; returns the deletion count."""
    query = f"""// Severs cross-pack content relationships touching managed or derived packs
MATCH (managed_pack:{ContentType.PACK})
WHERE {is_managed_or_derived("managed_pack")}
MATCH {_belongs_to_pack("inside", "managed_pack")}
MATCH (inside)-[r]-(outside)
WHERE NOT type(r) IN $preserved_types
AND {_has_a_pack("outside")}
AND NOT {_share_a_pack("inside", "outside")}
WITH DISTINCT r
DELETE r
RETURN count(*) AS severed"""
    result = run_query(
        tx,
        query,
        preserved_types=[
            relationship.value for relationship in PRESERVED_RELATIONSHIP_TYPES
        ],
    ).single()
    return int(result["severed"]) if result else 0


def isolate_managed_packs(tx: Transaction) -> List[Tuple[str, str]]:
    """Isolate every managed/derived pack (idempotent); the returned severed pairs must be pruned from the cached depends_on."""
    severed_dependencies = _sever_managed_pack_dependencies(tx)
    severed_relationships = _sever_cross_pack_content_relationships(tx)
    logger.info(
        f"Managed pack isolation severed {len(severed_dependencies) + severed_relationships} relationships: "
        f"{len(severed_dependencies)} pack dependencies and "
        f"{severed_relationships} cross-pack content relationships."
    )
    return sorted(severed_dependencies)
