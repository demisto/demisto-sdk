"""Cypher queries that isolate managed packs from the rest of the content graph.

A managed (or derived) pack ships to the Managed Content bucket as a
self-contained unit: everything it needs travels with it. Once the graph is
fully built, :func:`isolate_managed_packs` severs every relationship that
crosses the boundary of such a pack, in both directions, so that no managed pack
depends on anything and nothing depends on a managed pack.

Structural relationships are preserved: a managed pack must keep owning its
content items (``IN_PACK``), an integration must keep owning its commands
(``HAS_COMMAND``), and ApiModule imports (``IMPORTS``) are consumed by
unify/validate rather than shipped, so severing them would silently break
ApiModule change-impact detection.
"""

from typing import List, Set, Tuple

from neo4j import Transaction

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
    are_in_the_same_split_pack_family,
    is_managed_or_derived,
    run_query,
)

# Keep-list rather than a delete-list: an unknown relationship type - for
# example one replayed verbatim by return_preserved_relationships or carried by
# an imported bucket graph - is severed by default, which is the safe failure
# mode for an isolation guarantee.
PRESERVED_RELATIONSHIP_TYPES: Tuple[RelationshipType, ...] = (
    RelationshipType.IN_PACK,
    RelationshipType.HAS_COMMAND,
    RelationshipType.IMPORTS,
)

# A node belongs to a pack either by *being* that pack (zero hops) or by having
# an IN_PACK edge to it (one hop). The zero-hop case is what lets pack-targeted
# relationships (DEPENDS_ON, REFERENCES_PACK) be compared with content-item ones
# using a single expression.
_IN_PACK_HOPS = f"-[:{RelationshipType.IN_PACK}*0..1]->"


def _belongs_to_pack(node: str, pack: str) -> str:
    """Builds a pattern matching ``node`` against a pack it belongs to."""
    return f"({node}){_IN_PACK_HOPS}({pack})"


def _has_a_pack(node: str) -> str:
    """Builds a predicate that is true when a node belongs to some pack.

    Commands, connectors and ``not_in_repository`` stubs have no ``IN_PACK``
    edge and are not another pack, so relationships to them are never severed.
    """
    return f"EXISTS {{ {_belongs_to_pack(node, f'_any_pack:{ContentType.PACK}')} }}"


def _share_a_pack(node_a: str, node_b: str) -> str:
    """Builds a predicate that is true when both nodes belong to a common pack.

    A tightly-coupled content item belongs to **both** the origin pack and its
    derived twin, so a per-binding ``pack_a <> pack_b`` comparison would report
    the same edge as cross-pack under one binding and intra-pack under another,
    and delete legitimate intra-pack edges. The comparison must therefore be
    quantified over all packs: sever only when *no* pack contains both endpoints.
    """
    shared_pack = f"_shared_pack:{ContentType.PACK}"
    return (
        f"EXISTS {{ ({node_a}){_IN_PACK_HOPS}({shared_pack})"
        f"<-[:{RelationshipType.IN_PACK}*0..1]-({node_b}) }}"
    )


def _sever_managed_pack_dependencies(tx: Transaction) -> Set[Tuple[str, str]]:
    """Deletes every pack-level ``DEPENDS_ON`` edge that involves a managed pack.

    Both directions are covered by a single undirected-by-predicate match: the
    edge is deleted when either endpoint is managed or derived. Split-pack twins
    are matched as well, so a derived pack whose ``managed``/``is_derived``
    properties were not persisted by an older build is still isolated from its
    origin.

    Args:
        tx: The neo4j transaction.

    Returns:
        The ``(source_pack_id, target_pack_id)`` pairs whose edges were deleted.
    """
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
    """Deletes non-structural relationships crossing a managed pack's boundary.

    The match is anchored on managed packs (there are few of them) and expands
    to the nodes they contain, then walks every relationship of those nodes in
    both directions. An edge is severed only when the other endpoint belongs to
    a pack of its own and the two endpoints share no pack at all.

    Args:
        tx: The neo4j transaction.

    Returns:
        The number of relationships that were deleted.
    """
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
    """Isolates every managed and derived pack from the rest of the graph.

    Runs as a single dedicated step after the graph is fully built (including
    dependency calculation), so it sees every relationship regardless of how it
    entered the graph - parsed, calculated, imported or replayed. It is
    idempotent: a second run finds nothing left to sever and is a no-op.

    Args:
        tx: The neo4j transaction.

    Returns:
        The sorted ``(source_pack_id, target_pack_id)`` pairs of the pack-level
        ``DEPENDS_ON`` edges that were deleted. Callers holding a cached
        ``depends_on`` mapping (which is serialized to ``depends_on.json``) must
        prune these pairs from it before exporting, otherwise the artifact
        advertises dependencies that no longer exist in the graph.
    """
    severed_dependencies = _sever_managed_pack_dependencies(tx)
    severed_relationships = _sever_cross_pack_content_relationships(tx)
    logger.info(
        f"Managed pack isolation severed {len(severed_dependencies) + severed_relationships} relationships: "
        f"{len(severed_dependencies)} pack dependencies and "
        f"{severed_relationships} cross-pack content relationships."
    )
    return sorted(severed_dependencies)
