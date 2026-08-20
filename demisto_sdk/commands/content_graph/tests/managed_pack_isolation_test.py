"""Tests for the managed-pack isolation step.

The invariant under test: once the content graph is fully built, a pack with
``managed = true`` (or ``is_derived = true``) has no dependency or usage
relationship to anything, and nothing depends on or uses it.

Precisely:

- No pack-level ``DEPENDS_ON`` in either direction where an endpoint pack is
  managed or derived.
- No cross-pack content-item relationship (``USES``, ``TESTED_BY``,
  ``REFERENCES_INTEGRATION``, ...) where one endpoint's pack is managed/derived
  and the other endpoint lies outside that pack.
- ``IN_PACK``, ``HAS_COMMAND`` and ``IMPORTS`` survive - a managed pack still
  owns its content items.

Two layers of tests:

1. Seeded-graph tests. A small graph is written straight into neo4j so the exact
   topology under test - two ``IN_PACK`` edges on one item, endpoints with no
   pack at all, absent ``managed`` properties - can be expressed unambiguously,
   then :meth:`isolate_managed_packs` is run against it. These pin the isolation
   semantics themselves.
2. End-to-end tests. A real repository is parsed and built through
   ``create_content_graph``, proving the step is actually wired into the build
   and that the artifacts it exports agree with the graph.
"""

from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import pytest

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import (
    Neo4jContentGraphInterface as ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import labels_of
from TestSuite.repo import Repo

json = JSON_Handler()

# A relationship as asserted on: (source object_id, relationship type, target object_id).
Edge = Tuple[str, str, str]

# Every non-structural relationship type that may connect two content items.
# Each one must be severed when it crosses the boundary of a managed pack.
CROSS_PACK_RELATIONSHIP_TYPES: Tuple[RelationshipType, ...] = (
    RelationshipType.USES,
    RelationshipType.USES_BY_ID,
    RelationshipType.USES_BY_NAME,
    RelationshipType.USES_BY_CLI_NAME,
    RelationshipType.USES_COMMAND_OR_SCRIPT,
    RelationshipType.USES_PLAYBOOK,
    RelationshipType.TESTED_BY,
    RelationshipType.REFERENCES_INTEGRATION,
)

# Ids used by the seeded graphs. Named so each test reads as a specification.
MANAGED_PACK = "ManagedPack"
ORIGIN_PACK = "OriginPack"
TWIN_PACK = "OriginPackManaged"
REGULAR_PACK = "RegularPack"
OTHER_REGULAR_PACK = "OtherRegularPack"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def graph(mocker, tmp_path_factory) -> Iterator[ContentGraphInterface]:
    """Yields an interface over an empty graph, seeded by the test itself."""
    mocker.patch.object(
        neo4j_service, "NEO4J_DIR", new=tmp_path_factory.mktemp("neo4j")
    )
    with ContentGraphInterface() as interface:
        interface.clean_graph()
        yield interface
        interface.clean_graph()


# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------


def create_pack(
    interface: ContentGraphInterface,
    object_id: str,
    managed: Optional[bool] = None,
    is_derived: Optional[bool] = None,
    derived_from: Optional[str] = None,
) -> None:
    """Creates a Pack node.

    ``None`` is written as an absent property, which is how a graph built by an
    older SDK - or imported from a bucket - represents a pack that carries no
    ``managed`` flag at all.
    """
    interface.run_single_query(
        f"CREATE (pack:{labels_of(ContentType.PACK)} {{"
        "object_id: $object_id, content_type: $content_type, managed: $managed, "
        "is_derived: $is_derived, derived_from: $derived_from})",
        object_id=object_id,
        content_type=ContentType.PACK.value,
        managed=managed,
        is_derived=is_derived,
        derived_from=derived_from,
    )


def create_item(
    interface: ContentGraphInterface,
    object_id: str,
    content_type: ContentType = ContentType.SCRIPT,
    in_packs: Tuple[str, ...] = (),
    not_in_repository: bool = False,
) -> None:
    """Creates a content item node and its ``IN_PACK`` edges.

    ``in_packs`` may hold more than one pack: a tightly-coupled item belongs to
    both its origin pack and that pack's derived twin.
    """
    interface.run_single_query(
        f"CREATE (item:{labels_of(content_type)} {{"
        "object_id: $object_id, content_type: $content_type, "
        "not_in_repository: $not_in_repository})",
        object_id=object_id,
        content_type=content_type.value,
        not_in_repository=not_in_repository,
    )
    for pack in in_packs:
        create_relationship(interface, object_id, RelationshipType.IN_PACK, pack)


def create_relationship(
    interface: ContentGraphInterface,
    source_id: str,
    relationship_type: RelationshipType,
    target_id: str,
) -> None:
    """Creates a relationship of the given type between two existing nodes."""
    # A relationship type cannot be parameterized in cypher, so it is
    # interpolated - through the enum, which rejects anything unknown.
    validated_type = RelationshipType(relationship_type).value
    interface.run_single_query(
        "MATCH (source {object_id: $source_id}) "
        "MATCH (target {object_id: $target_id}) "
        f"CREATE (source)-[:{validated_type}]->(target)",
        source_id=source_id,
        target_id=target_id,
    )


def edges_of(interface: ContentGraphInterface) -> Set[Edge]:
    """Returns every relationship in the graph as a comparable set."""
    rows: List[Dict[str, Any]] = interface.run_single_query(
        "MATCH (source)-[relationship]->(target) "
        "RETURN source.object_id AS source, type(relationship) AS type, "
        "target.object_id AS target"
    )
    return {(row["source"], row["type"], row["target"]) for row in rows}


def pack_dependencies_of(interface: ContentGraphInterface, pack_id: str) -> Set[str]:
    """Returns the ids of the packs the given pack depends on, in either direction."""
    return {
        source if target == pack_id else target
        for source, relationship_type, target in edges_of(interface)
        if relationship_type == RelationshipType.DEPENDS_ON.value
        and pack_id in (source, target)
    }


# ---------------------------------------------------------------------------
# 1. A managed pack has zero outgoing dependencies
# ---------------------------------------------------------------------------


class TestManagedPackHasNoOutgoingDependencies:
    """A managed pack must not reach outside itself, at pack or item level."""

    def test_outgoing_pack_dependency_is_severed(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_pack(graph, REGULAR_PACK)
        create_relationship(
            graph, MANAGED_PACK, RelationshipType.DEPENDS_ON, REGULAR_PACK
        )

        graph.isolate_managed_packs()

        assert (
            pack_dependencies_of(graph, MANAGED_PACK) == set()
        ), "a managed pack must carry no outgoing DEPENDS_ON after isolation"

    def test_outgoing_cross_pack_uses_is_severed(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_pack(graph, REGULAR_PACK)
        create_item(graph, "ManagedScript", in_packs=(MANAGED_PACK,))
        create_item(graph, "RegularScript", in_packs=(REGULAR_PACK,))
        create_relationship(
            graph, "ManagedScript", RelationshipType.USES, "RegularScript"
        )

        graph.isolate_managed_packs()

        assert ("ManagedScript", RelationshipType.USES.value, "RegularScript") not in (
            edges_of(graph)
        ), "a managed pack's item must not USES an item of another pack"

    def test_severed_pack_dependency_pairs_are_returned(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_pack(graph, REGULAR_PACK)
        create_relationship(
            graph, MANAGED_PACK, RelationshipType.DEPENDS_ON, REGULAR_PACK
        )

        severed = graph.isolate_managed_packs()

        assert severed == [
            (MANAGED_PACK, REGULAR_PACK)
        ], "the severed pairs must be reported so callers can prune depends_on.json"

    @pytest.mark.parametrize("relationship_type", CROSS_PACK_RELATIONSHIP_TYPES)
    def test_every_non_structural_type_is_severed_outbound(
        self, graph: ContentGraphInterface, relationship_type: RelationshipType
    ) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_pack(graph, REGULAR_PACK)
        create_item(graph, "ManagedItem", in_packs=(MANAGED_PACK,))
        create_item(graph, "RegularItem", in_packs=(REGULAR_PACK,))
        create_relationship(graph, "ManagedItem", relationship_type, "RegularItem")

        graph.isolate_managed_packs()

        assert (
            "ManagedItem",
            relationship_type.value,
            "RegularItem",
        ) not in edges_of(
            graph
        ), f"{relationship_type.value} must be severed when it leaves a managed pack"

    def test_references_pack_to_another_pack_is_severed(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_pack(graph, REGULAR_PACK)
        create_item(graph, "ManagedItem", in_packs=(MANAGED_PACK,))
        create_relationship(
            graph, "ManagedItem", RelationshipType.REFERENCES_PACK, REGULAR_PACK
        )

        graph.isolate_managed_packs()

        assert (
            "ManagedItem",
            RelationshipType.REFERENCES_PACK.value,
            REGULAR_PACK,
        ) not in edges_of(
            graph
        ), "REFERENCES_PACK is a soft reference to a foreign pack, not ownership"


# ---------------------------------------------------------------------------
# 2. Nothing depends on a managed pack
# ---------------------------------------------------------------------------


class TestNothingDependsOnAManagedPack:
    """Isolation is symmetric: the inbound direction is severed as well."""

    def test_inbound_pack_dependency_is_severed(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_pack(graph, REGULAR_PACK)
        create_relationship(
            graph, REGULAR_PACK, RelationshipType.DEPENDS_ON, MANAGED_PACK
        )

        graph.isolate_managed_packs()

        assert (
            pack_dependencies_of(graph, MANAGED_PACK) == set()
        ), "no pack may declare a dependency on a managed pack"

    def test_inbound_cross_pack_uses_is_severed(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_pack(graph, REGULAR_PACK)
        create_item(graph, "ManagedScript", in_packs=(MANAGED_PACK,))
        create_item(graph, "RegularScript", in_packs=(REGULAR_PACK,))
        create_relationship(
            graph, "RegularScript", RelationshipType.USES, "ManagedScript"
        )

        graph.isolate_managed_packs()

        assert ("RegularScript", RelationshipType.USES.value, "ManagedScript") not in (
            edges_of(graph)
        ), "a regular pack's item must not USES an item of a managed pack"

    @pytest.mark.parametrize("relationship_type", CROSS_PACK_RELATIONSHIP_TYPES)
    def test_every_non_structural_type_is_severed_inbound(
        self, graph: ContentGraphInterface, relationship_type: RelationshipType
    ) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_pack(graph, REGULAR_PACK)
        create_item(graph, "ManagedItem", in_packs=(MANAGED_PACK,))
        create_item(graph, "RegularItem", in_packs=(REGULAR_PACK,))
        create_relationship(graph, "RegularItem", relationship_type, "ManagedItem")

        graph.isolate_managed_packs()

        assert (
            "RegularItem",
            relationship_type.value,
            "ManagedItem",
        ) not in edges_of(
            graph
        ), f"{relationship_type.value} must be severed when it enters a managed pack"


# ---------------------------------------------------------------------------
# 3. Derived packs are isolated too
# ---------------------------------------------------------------------------


class TestDerivedPacksAreIsolated:
    """``is_derived`` alone is enough to isolate, even without ``managed``."""

    def test_derived_pack_carrying_both_flags_is_isolated(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(
            graph, TWIN_PACK, managed=True, is_derived=True, derived_from=ORIGIN_PACK
        )
        create_pack(graph, REGULAR_PACK)
        create_relationship(graph, TWIN_PACK, RelationshipType.DEPENDS_ON, REGULAR_PACK)

        graph.isolate_managed_packs()

        assert pack_dependencies_of(graph, TWIN_PACK) == set()

    def test_derived_pack_without_the_managed_flag_is_isolated(
        self, graph: ContentGraphInterface
    ) -> None:
        """``managed`` may be absent on graphs written by an older build.

        ``is_derived`` must then carry the isolation on its own, otherwise a
        bare ``managed = true`` predicate silently matches nothing.
        """
        create_pack(graph, TWIN_PACK, is_derived=True, derived_from=ORIGIN_PACK)
        create_pack(graph, REGULAR_PACK)
        create_relationship(graph, REGULAR_PACK, RelationshipType.DEPENDS_ON, TWIN_PACK)

        graph.isolate_managed_packs()

        assert pack_dependencies_of(graph, TWIN_PACK) == set()

    def test_derived_pack_with_managed_false_is_isolated(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(
            graph, TWIN_PACK, managed=False, is_derived=True, derived_from=ORIGIN_PACK
        )
        create_pack(graph, REGULAR_PACK)
        create_item(graph, "TwinItem", in_packs=(TWIN_PACK,))
        create_item(graph, "RegularItem", in_packs=(REGULAR_PACK,))
        create_relationship(graph, "TwinItem", RelationshipType.USES, "RegularItem")

        graph.isolate_managed_packs()

        assert ("TwinItem", RelationshipType.USES.value, "RegularItem") not in (
            edges_of(graph)
        ), "an explicit `managed: false` must not defeat `is_derived: true`"

    def test_dependency_between_a_pack_and_its_own_twin_is_severed(
        self, graph: ContentGraphInterface
    ) -> None:
        """A pack and its twin are two representations of one source directory."""
        create_pack(graph, ORIGIN_PACK)
        create_pack(
            graph, TWIN_PACK, managed=True, is_derived=True, derived_from=ORIGIN_PACK
        )
        create_relationship(graph, ORIGIN_PACK, RelationshipType.DEPENDS_ON, TWIN_PACK)

        graph.isolate_managed_packs()

        assert pack_dependencies_of(graph, TWIN_PACK) == set()

    def test_twin_dependency_is_severed_by_family_key_alone(
        self, graph: ContentGraphInterface
    ) -> None:
        """``derived_from`` alone identifies a twin pair.

        Both flags may be missing on a pack imported from an externally built
        bucket graph; the shared family key is then the only thing left that
        marks the two nodes as one source directory, and a pack is never
        dependent on another representation of itself.
        """
        create_pack(graph, ORIGIN_PACK)
        create_pack(graph, TWIN_PACK, derived_from=ORIGIN_PACK)
        create_relationship(graph, ORIGIN_PACK, RelationshipType.DEPENDS_ON, TWIN_PACK)

        severed = graph.isolate_managed_packs()

        assert severed == [(ORIGIN_PACK, TWIN_PACK)]
        assert pack_dependencies_of(graph, TWIN_PACK) == set()


# ---------------------------------------------------------------------------
# 4. Structural relationships survive
# ---------------------------------------------------------------------------


class TestStructuralRelationshipsSurvive:
    """A managed pack keeps owning its content, and its items their commands."""

    def test_in_pack_edges_of_a_managed_pack_survive(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_pack(graph, REGULAR_PACK)
        create_item(graph, "ManagedScript", in_packs=(MANAGED_PACK,))
        create_item(graph, "RegularScript", in_packs=(REGULAR_PACK,))
        create_relationship(
            graph, "ManagedScript", RelationshipType.USES, "RegularScript"
        )

        graph.isolate_managed_packs()

        assert (
            "ManagedScript",
            RelationshipType.IN_PACK.value,
            MANAGED_PACK,
        ) in edges_of(graph), "a managed pack must still own its content items"

    def test_has_command_edges_inside_a_managed_pack_survive(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_item(
            graph,
            "ManagedIntegration",
            content_type=ContentType.INTEGRATION,
            in_packs=(MANAGED_PACK,),
        )
        create_item(graph, "managed-command", content_type=ContentType.COMMAND)
        create_relationship(
            graph,
            "ManagedIntegration",
            RelationshipType.HAS_COMMAND,
            "managed-command",
        )

        graph.isolate_managed_packs()

        assert (
            "ManagedIntegration",
            RelationshipType.HAS_COMMAND.value,
            "managed-command",
        ) in edges_of(
            graph
        ), "deleting HAS_COMMAND would orphan commands and break command lookup"

    def test_api_module_imports_out_of_a_managed_pack_survive(
        self, graph: ContentGraphInterface
    ) -> None:
        """``IMPORTS`` is consumed by unify/validate, not shipped.

        It is almost always cross-pack (into ``ApiModules``), so severing it
        would silently break ApiModule change-impact detection.
        """
        create_pack(graph, MANAGED_PACK, managed=True)
        create_pack(graph, "ApiModules")
        create_item(graph, "ManagedScript", in_packs=(MANAGED_PACK,))
        create_item(graph, "TestApiModule", in_packs=("ApiModules",))
        create_relationship(
            graph, "ManagedScript", RelationshipType.IMPORTS, "TestApiModule"
        )

        graph.isolate_managed_packs()

        assert (
            "ManagedScript",
            RelationshipType.IMPORTS.value,
            "TestApiModule",
        ) in edges_of(graph)


# ---------------------------------------------------------------------------
# 5. Intra-pack edges are not severed
# ---------------------------------------------------------------------------


class TestIntraPackEdgesAreNotSevered:
    """Sever only when *no* pack contains both endpoints."""

    def test_edge_between_two_items_of_the_same_managed_pack_survives(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_item(graph, "ManagedScript", in_packs=(MANAGED_PACK,))
        create_item(graph, "AnotherManagedScript", in_packs=(MANAGED_PACK,))
        create_relationship(
            graph, "ManagedScript", RelationshipType.USES, "AnotherManagedScript"
        )

        graph.isolate_managed_packs()

        assert (
            "ManagedScript",
            RelationshipType.USES.value,
            "AnotherManagedScript",
        ) in edges_of(graph), "a managed pack's internal wiring must stay intact"

    def test_edge_between_items_sharing_the_origin_pack_of_a_twin_survives(
        self, graph: ContentGraphInterface
    ) -> None:
        """The shared-pack trap.

        A tightly-coupled item has two ``IN_PACK`` edges - to its origin pack and
        to that pack's derived twin. A per-binding ``pack_a <> pack_b`` test sees
        such an edge as cross-pack under the twin binding and intra-pack under
        the origin binding, and deletes a legitimate intra-pack edge.
        """
        create_pack(graph, ORIGIN_PACK)
        create_pack(
            graph, TWIN_PACK, managed=True, is_derived=True, derived_from=ORIGIN_PACK
        )
        # Tightly coupled: lives in the origin pack *and* in the twin.
        create_item(graph, "CoupledIntegration", in_packs=(ORIGIN_PACK, TWIN_PACK))
        # Loosely coupled: stays in the origin pack only.
        create_item(graph, "LooseScript", in_packs=(ORIGIN_PACK,))
        create_relationship(
            graph, "CoupledIntegration", RelationshipType.USES, "LooseScript"
        )

        graph.isolate_managed_packs()

        assert (
            "CoupledIntegration",
            RelationshipType.USES.value,
            "LooseScript",
        ) in edges_of(
            graph
        ), "both endpoints share the origin pack, so the edge is not cross-pack"

    def test_both_in_pack_edges_of_a_tightly_coupled_item_survive(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, ORIGIN_PACK)
        create_pack(
            graph, TWIN_PACK, managed=True, is_derived=True, derived_from=ORIGIN_PACK
        )
        create_item(graph, "CoupledIntegration", in_packs=(ORIGIN_PACK, TWIN_PACK))

        graph.isolate_managed_packs()

        assert {
            ("CoupledIntegration", RelationshipType.IN_PACK.value, ORIGIN_PACK),
            ("CoupledIntegration", RelationshipType.IN_PACK.value, TWIN_PACK),
        } <= edges_of(graph)


# ---------------------------------------------------------------------------
# 6. Pack-less endpoints are untouched
# ---------------------------------------------------------------------------


class TestPackLessEndpointsAreUntouched:
    """A node outside every pack is not "another pack", so it is not severed."""

    def test_edge_to_a_command_node_survives(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_item(graph, "ManagedPlaybook", in_packs=(MANAGED_PACK,))
        # Command nodes are reachable via HAS_COMMAND only, never via IN_PACK.
        create_item(graph, "some-command", content_type=ContentType.COMMAND)
        create_relationship(
            graph,
            "ManagedPlaybook",
            RelationshipType.USES_COMMAND_OR_SCRIPT,
            "some-command",
        )

        graph.isolate_managed_packs()

        assert (
            "ManagedPlaybook",
            RelationshipType.USES_COMMAND_OR_SCRIPT.value,
            "some-command",
        ) in edges_of(graph), "severing this would break command resolution"

    def test_tested_by_a_not_in_repository_stub_survives(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_item(graph, "ManagedIntegration", in_packs=(MANAGED_PACK,))
        create_item(
            graph,
            "MissingTestPlaybook",
            content_type=ContentType.TEST_PLAYBOOK,
            not_in_repository=True,
        )
        create_relationship(
            graph,
            "ManagedIntegration",
            RelationshipType.TESTED_BY,
            "MissingTestPlaybook",
        )

        graph.isolate_managed_packs()

        assert (
            "ManagedIntegration",
            RelationshipType.TESTED_BY.value,
            "MissingTestPlaybook",
        ) in edges_of(
            graph
        ), "a not_in_repository stub has no IN_PACK edge and is not another pack"

    def test_edge_to_a_connector_survives(self, graph: ContentGraphInterface) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_item(graph, "ManagedScript", in_packs=(MANAGED_PACK,))
        # Connectors are top-level content with no enclosing pack.
        create_item(graph, "SomeConnector", content_type=ContentType.CONNECTOR)
        create_relationship(
            graph, "ManagedScript", RelationshipType.USES, "SomeConnector"
        )

        graph.isolate_managed_packs()

        assert (
            "ManagedScript",
            RelationshipType.USES.value,
            "SomeConnector",
        ) in edges_of(graph)


# ---------------------------------------------------------------------------
# 7. Regular pack relationships are untouched
# ---------------------------------------------------------------------------


class TestRegularPackRelationshipsAreUntouched:
    """Isolation must not over-delete: only managed boundaries are cut."""

    def test_dependency_between_two_regular_packs_survives(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, REGULAR_PACK)
        create_pack(graph, OTHER_REGULAR_PACK)
        create_relationship(
            graph, REGULAR_PACK, RelationshipType.DEPENDS_ON, OTHER_REGULAR_PACK
        )

        graph.isolate_managed_packs()

        assert (
            REGULAR_PACK,
            RelationshipType.DEPENDS_ON.value,
            OTHER_REGULAR_PACK,
        ) in edges_of(graph)

    def test_cross_pack_uses_between_two_regular_packs_survives(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, REGULAR_PACK)
        create_pack(graph, OTHER_REGULAR_PACK)
        create_item(graph, "RegularScript", in_packs=(REGULAR_PACK,))
        create_item(graph, "OtherRegularScript", in_packs=(OTHER_REGULAR_PACK,))
        create_relationship(
            graph, "RegularScript", RelationshipType.USES, "OtherRegularScript"
        )

        graph.isolate_managed_packs()

        assert (
            "RegularScript",
            RelationshipType.USES.value,
            "OtherRegularScript",
        ) in edges_of(graph)

    def test_a_graph_without_managed_packs_is_left_exactly_as_it_was(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, REGULAR_PACK)
        create_pack(graph, OTHER_REGULAR_PACK)
        create_item(graph, "RegularScript", in_packs=(REGULAR_PACK,))
        create_item(graph, "OtherRegularScript", in_packs=(OTHER_REGULAR_PACK,))
        create_relationship(
            graph, "RegularScript", RelationshipType.USES, "OtherRegularScript"
        )
        create_relationship(
            graph, REGULAR_PACK, RelationshipType.DEPENDS_ON, OTHER_REGULAR_PACK
        )
        edges_before = edges_of(graph)

        severed = graph.isolate_managed_packs()

        assert severed == []
        assert edges_of(graph) == edges_before


# ---------------------------------------------------------------------------
# 8. Idempotency
# ---------------------------------------------------------------------------


class TestIsolationIsIdempotent:
    """Running the step twice must be indistinguishable from running it once."""

    @staticmethod
    def _seed_mixed_graph(interface: ContentGraphInterface) -> None:
        create_pack(interface, MANAGED_PACK, managed=True)
        create_pack(interface, REGULAR_PACK)
        create_pack(interface, OTHER_REGULAR_PACK)
        create_item(interface, "ManagedScript", in_packs=(MANAGED_PACK,))
        create_item(interface, "RegularScript", in_packs=(REGULAR_PACK,))
        create_item(interface, "OtherRegularScript", in_packs=(OTHER_REGULAR_PACK,))
        create_relationship(
            interface, MANAGED_PACK, RelationshipType.DEPENDS_ON, REGULAR_PACK
        )
        create_relationship(
            interface, "ManagedScript", RelationshipType.USES, "RegularScript"
        )
        create_relationship(
            interface, "RegularScript", RelationshipType.USES, "OtherRegularScript"
        )

    def test_second_run_severs_nothing_and_returns_an_empty_list(
        self, graph: ContentGraphInterface
    ) -> None:
        self._seed_mixed_graph(graph)
        first_run = graph.isolate_managed_packs()

        second_run = graph.isolate_managed_packs()

        assert first_run == [(MANAGED_PACK, REGULAR_PACK)]
        assert second_run == []

    def test_second_run_leaves_the_graph_unchanged(
        self, graph: ContentGraphInterface
    ) -> None:
        self._seed_mixed_graph(graph)
        graph.isolate_managed_packs()
        edges_after_first_run = edges_of(graph)

        graph.isolate_managed_packs()

        assert edges_of(graph) == edges_after_first_run


# ---------------------------------------------------------------------------
# 9. depends_on artifact consistency
# ---------------------------------------------------------------------------


class TestDependsOnArtifactConsistency:
    """``depends_on.json`` is serialized from the cached mapping, so it must be pruned."""

    def test_severed_pairs_are_pruned_from_the_cached_mapping(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_pack(graph, REGULAR_PACK)
        create_pack(graph, OTHER_REGULAR_PACK)
        create_relationship(
            graph, MANAGED_PACK, RelationshipType.DEPENDS_ON, REGULAR_PACK
        )
        create_relationship(
            graph, REGULAR_PACK, RelationshipType.DEPENDS_ON, OTHER_REGULAR_PACK
        )
        graph._depends_on = {
            MANAGED_PACK: {REGULAR_PACK: [["ManagedScript", "RegularScript"]]},
            REGULAR_PACK: {
                OTHER_REGULAR_PACK: [["RegularScript", "OtherRegularScript"]]
            },
        }

        graph.isolate_managed_packs()

        assert graph._depends_on == {
            REGULAR_PACK: {
                OTHER_REGULAR_PACK: [["RegularScript", "OtherRegularScript"]]
            }
        }, "the artifact must not advertise dependencies that no longer exist"

    def test_a_source_left_with_no_targets_is_dropped_entirely(
        self, graph: ContentGraphInterface
    ) -> None:
        create_pack(graph, MANAGED_PACK, managed=True)
        create_pack(graph, REGULAR_PACK)
        create_relationship(
            graph, REGULAR_PACK, RelationshipType.DEPENDS_ON, MANAGED_PACK
        )
        graph._depends_on = {
            REGULAR_PACK: {MANAGED_PACK: [["RegularScript", "ManagedScript"]]}
        }

        graph.isolate_managed_packs()

        assert graph._depends_on == {}


# ---------------------------------------------------------------------------
# End-to-end: a real repository, parsed and built
# ---------------------------------------------------------------------------


def build_repo_with_a_managed_pack(repo: Repo) -> None:
    """Creates a repository whose content crosses a managed pack's boundary.

    - ``RegularPackA`` holds ``RegularScriptA``.
    - ``RegularPackB``'s script uses ``RegularScriptA`` - a regular cross-pack
      dependency that must survive, and that keeps ``depends_on.json`` non-empty.
    - ``ManagedPack`` is ``managed`` and its script uses ``RegularScriptA``
      - an outbound crossing.
    - ``RegularPackC``'s script uses ``ManagedScript`` - an inbound crossing.
    """
    regular_pack_a = repo.create_pack("RegularPackA")
    regular_pack_a.create_script("RegularScriptA")

    regular_pack_b = repo.create_pack("RegularPackB")
    regular_pack_b.create_script(
        "RegularScriptB", code='demisto.execute_command("RegularScriptA", dArgs)'
    )

    managed_pack = repo.create_pack(MANAGED_PACK)
    managed_pack.pack_metadata.update({"managed": True, "source": "testfeature"})
    managed_pack.create_script(
        "ManagedScript", code='demisto.execute_command("RegularScriptA", dArgs)'
    )

    regular_pack_c = repo.create_pack("RegularPackC")
    regular_pack_c.create_script(
        "RegularScriptC", code='demisto.execute_command("ManagedScript", dArgs)'
    )


class TestManagedPackIsolationEndToEnd:
    """Proves the step is wired into ``create_content_graph`` and into its artifacts."""

    def test_a_built_graph_satisfies_the_isolation_invariant(
        self, graph_repo: Repo
    ) -> None:
        build_repo_with_a_managed_pack(graph_repo)

        interface = graph_repo.create_graph()

        edges = edges_of(interface)
        crossing_edges = {
            (source, relationship_type, target)
            for source, relationship_type, target in edges
            if relationship_type
            not in (
                RelationshipType.IN_PACK.value,
                RelationshipType.HAS_COMMAND.value,
                RelationshipType.IMPORTS.value,
            )
            and {source, target} & {MANAGED_PACK, "ManagedScript"}
        }
        assert (
            crossing_edges == set()
        ), f"nothing may cross the managed pack's boundary, found: {crossing_edges}"
        assert (
            "ManagedScript",
            RelationshipType.IN_PACK.value,
            MANAGED_PACK,
        ) in edges, "the managed pack must still own its script"
        assert (
            "RegularScriptB",
            RelationshipType.USES.value,
            "RegularScriptA",
        ) in edges, "regular cross-pack usage must not be collateral damage"

    def test_depends_on_json_references_no_managed_pack(
        self, graph_repo: Repo, tmp_path: Path
    ) -> None:
        build_repo_with_a_managed_pack(graph_repo)

        interface = graph_repo.create_graph(output_path=tmp_path)

        depends_on_path = (
            interface.import_path / ContentGraphInterface.DEPENDS_ON_FILE_NAME
        )
        assert (
            depends_on_path.exists()
        ), "the fixture's regular packs must produce a non-empty depends_on.json"
        depends_on: Dict[str, Dict[str, Any]] = json.loads(depends_on_path.read_text())
        assert (
            MANAGED_PACK not in depends_on
        ), "a managed pack must not appear as a dependency source"
        for source, targets in depends_on.items():
            assert (
                MANAGED_PACK not in targets
            ), f"{source} must not advertise a dependency on the managed pack"
