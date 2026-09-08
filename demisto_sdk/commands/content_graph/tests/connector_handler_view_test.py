"""Unit tests for the handler-visible-fields walker.

Covers the exhaustive Section 6 test matrix in
``plans/handler-visible-fields-walker.md``:

- One test per origin (per bug documented in §3)
- Regression tests for the four bugs the walker fixes
- Regression tests for the finalized decisions (Q1 no-dedup,
  Q2 raw_dict sidecar)
- Missing-file / empty-block graceful-handling tests
- Multi-handler cross-contamination tests
- Public ``Connector`` method tests

Every test builds a minimal on-disk connector via
:func:`_build_connector` (a lightweight factory tailored to this suite)
and asserts on the walker output. The factory writes only what each test
needs — no shared per-test connector fixture, so a change in one test's
manifests can never break another.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as _yaml
from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.objects.connector_handler_view import (
    FieldOrigin,
    walk_visible_fields,
)
from demisto_sdk.commands.content_graph.parsers.connector import ConnectorParser


# ============================================================
# Test fixture factory
# ============================================================


def _default_connector_yaml(connector_id: str) -> Dict[str, Any]:
    return {
        "id": connector_id,
        "metadata": {
            "title": "Test Connector",
            "description": "A test connector for walker unit tests",
            "version": "1.0.0",
            "categories": ["Test"],
            "tags": ["test"],
            "domain": "test",
            "vendor": "TestVendor",
            "publisher": "TestPublisher",
            "ownership": {
                "team": "xsoar",
                "maintainers": ["@xsoar-content"],
            },
        },
        "settings": {"grouped": False},
    }


def _default_handler_yaml(
    handler_id: str = "xsoar-test",
    module: str = "xsoar",
    capabilities: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "id": handler_id,
        "enabled": True,
        "metadata": {
            "version": "1.0.0",
            "description": "Test handler",
            "module": module,
            "tags": ["test"],
            "ownership": {
                "team": "xsoar",
                "maintainers": ["@xsoar-content"],
            },
        },
        "triggering": {
            "type": "PUB_SUB",
            "labels": {"xsoar-integration-id": "TestIntegration"},
            "args": {},
        },
        "capabilities": capabilities or [
            {"id": "test-capability", "auth_options": [{"id": "default"}]}
        ],
        "test_connection": {"type": "ENDPOINT"},
    }


def _build_connector(
    tmp_path: Path,
    *,
    connector_id: str = "test-connector",
    grouped: bool = False,
    connection: Optional[Dict[str, Any]] = None,
    capabilities: Optional[Dict[str, Any]] = None,
    configurations: Optional[Dict[str, Any]] = None,
    handlers: Optional[List[Dict[str, Any]]] = None,
    serializers: Optional[Dict[str, Dict[str, Any]]] = None,
    write_connection: bool = True,
    write_capabilities: bool = True,
    write_configurations: bool = False,
) -> Connector:
    """Build a Connector by writing minimal YAML files under ``tmp_path``
    and parsing them via :class:`ConnectorParser`.

    Args:
        tmp_path: pytest's ``tmp_path`` fixture directory.
        connector_id: id used as directory name and in connector.yaml.
        grouped: sets ``settings.grouped``.
        connection: full contents of ``connection.yaml`` (dict). Ignored
            when ``write_connection=False``.
        capabilities: full contents of ``capabilities.yaml`` (dict).
            Ignored when ``write_capabilities=False``.
        configurations: full contents of ``configurations.yaml`` (dict).
            Only written when ``write_configurations=True``.
        handlers: list of full handler.yaml dicts. If None, a single
            default xsoar handler is written.
        serializers: ``{handler_id: serializer_dict}`` mapping — writes a
            ``serializer.yaml`` inside that handler's directory.
        write_connection / write_capabilities / write_configurations:
            controls whether the corresponding sub-file is written to
            disk (for missing-file tests).
    """
    conn_dir = tmp_path / connector_id
    conn_dir.mkdir(parents=True)

    # connector.yaml
    conn_yaml = _default_connector_yaml(connector_id)
    conn_yaml["settings"]["grouped"] = grouped
    with (conn_dir / "connector.yaml").open("w") as f:
        _yaml.dump(conn_yaml, f)

    if write_connection:
        with (conn_dir / "connection.yaml").open("w") as f:
            _yaml.dump(
                connection
                if connection is not None
                else {
                    "metadata": {"title": "Connection"},
                    "profiles": [
                        {
                            "id": "default",
                            "type": "plain",
                            "configurations": [
                                {"fields": [{"id": "api_url"}]},
                            ],
                        }
                    ],
                },
                f,
            )

    if write_capabilities:
        with (conn_dir / "capabilities.yaml").open("w") as f:
            _yaml.dump(
                capabilities
                if capabilities is not None
                else {
                    "metadata": {"title": "Capabilities"},
                    "capabilities": [
                        {"id": "test-capability", "title": "Test Capability"}
                    ],
                },
                f,
            )

    if write_configurations and configurations is not None:
        with (conn_dir / "configurations.yaml").open("w") as f:
            _yaml.dump(configurations, f)

    # Handler(s)
    handlers_root = conn_dir / "components" / "handlers"
    handlers_root.mkdir(parents=True)
    handler_list = handlers or [_default_handler_yaml()]
    for h in handler_list:
        h_id = h["id"]
        h_dir = handlers_root / h_id
        h_dir.mkdir()
        with (h_dir / "handler.yaml").open("w") as f:
            _yaml.dump(h, f)
        if serializers and h_id in serializers:
            with (h_dir / "serializer.yaml").open("w") as f:
                _yaml.dump(serializers[h_id], f)

    parser = ConnectorParser(
        conn_dir,
        pack_marketplaces=list(MarketplaceVersions),
        pack_supported_modules=[],
    )
    return Connector.from_orm(parser)


def _get_handler(connector: Connector, handler_id: str):
    for h in connector.handlers:
        if h.id == handler_id:
            return h
    raise AssertionError(
        f"Handler {handler_id!r} not found in connector; have {[h.id for h in connector.handlers]!r}"
    )


# ============================================================
# Section 6.1 — Standard connector, all four origins
# ============================================================


class TestStandardConnectorAllOrigins:
    """Section 6 row 1: standard connector, all four origins."""

    def test_all_four_origins_present(self, tmp_path):
        """
        Given: a standard connector with a field on each of the 4 origins
               (connection.general, connection.profile, capabilities.general,
               configurations.general, configurations.<cap>).
        When: walk_visible_fields runs.
        Then: one HandlerVisibleField per field with the correct origin;
              raw_id == runtime_name; is_serialized == False.
        """
        connector = _build_connector(
            tmp_path,
            connection={
                "metadata": {"title": "Connection"},
                "general_configurations": {
                    "configurations": [
                        {"fields": [{"id": "conn_general_field"}]},
                    ]
                },
                "profiles": [
                    {
                        "id": "default",
                        "type": "plain",
                        "configurations": [
                            {"fields": [{"id": "profile_field"}]},
                        ],
                    }
                ],
            },
            capabilities={
                "metadata": {"title": "Capabilities"},
                "general_configurations": {
                    "configurations": [
                        {"fields": [{"id": "caps_general_field"}]},
                    ]
                },
                "capabilities": [{"id": "test-capability"}],
            },
            configurations={
                "general_configurations": {
                    "configurations": [
                        {"fields": [{"id": "configs_general_field"}]},
                    ]
                },
                "configurations": [
                    {
                        "id": "test-capability",
                        "configurations": [
                            {"fields": [{"id": "cap_field"}]},
                        ],
                    }
                ],
            },
            write_configurations=True,
        )
        handler = _get_handler(connector, "xsoar-test")
        fields = walk_visible_fields(connector, handler)

        by_origin = {f.origin: f for f in fields}
        assert set(by_origin.keys()) == {
            FieldOrigin.CONNECTION_GENERAL,
            FieldOrigin.CONNECTION_PROFILE,
            FieldOrigin.CAPABILITIES_GENERAL,
            FieldOrigin.CONFIGURATIONS_GENERAL,
            FieldOrigin.CONFIGURATIONS_CAPABILITY,
        }, f"Missing origins; got {sorted(o.value for o in by_origin.keys())}"

        # No serializer → raw_id == runtime_name; not serialized.
        for f in fields:
            assert f.raw_id == f.runtime_name
            assert f.is_serialized is False

        # Attributed context per §2.1.
        assert by_origin[FieldOrigin.CONNECTION_PROFILE].profile_id == "default"
        assert (
            by_origin[FieldOrigin.CONFIGURATIONS_CAPABILITY].capability_id
            == "test-capability"
        )
        # Standard connector: no sub-caps.
        assert (
            by_origin[FieldOrigin.CONFIGURATIONS_CAPABILITY].parent_capability_id
            is None
        )


# ============================================================
# Section 6 rows 3-6 — view_group / required_for_capabilities scoping
# (grouped-connector leak = Bug 1)
# ============================================================


class TestGeneralConfigurationsScoping:
    """Section 6 rows 3-6 + Bug 1 regression."""

    def test_grouped_connector_view_group_leak_regression(self, tmp_path):
        """
        Given: a grouped connector with two handlers each auth-binding
               to a distinct profile, each profile carrying a distinct
               view_group. Two general_configurations groups on
               connection.yaml, each scoped to a different view_group.
        When: walk_visible_fields runs per handler.
        Then: Handler A sees only its view_group's field; Handler B sees
              only its own. This is Bug 1 (view_group leak) regression.
        """
        connector = _build_connector(
            tmp_path,
            grouped=True,
            connection={
                "metadata": {"title": "Connection"},
                "view_groups": [
                    {"id": "vg-a", "label": "A"},
                    {"id": "vg-b", "label": "B"},
                ],
                "general_configurations": {
                    "configurations": [
                        {
                            "view_group": "vg-a",
                            "fields": [{"id": "field_only_for_a"}],
                        },
                        {
                            "view_group": "vg-b",
                            "fields": [{"id": "field_only_for_b"}],
                        },
                    ]
                },
                "profiles": [
                    {
                        "id": "profile-a",
                        "type": "plain",
                        "view_group": "vg-a",
                        "configurations": [{"fields": [{"id": "profile_a_field"}]}],
                    },
                    {
                        "id": "profile-b",
                        "type": "plain",
                        "view_group": "vg-b",
                        "configurations": [{"fields": [{"id": "profile_b_field"}]}],
                    },
                ],
            },
            capabilities={
                "metadata": {"title": "Capabilities"},
                "capabilities": [{"id": "cap-shared"}],
            },
            handlers=[
                _default_handler_yaml(
                    "xsoar-a",
                    capabilities=[
                        {"id": "cap-shared", "auth_options": [{"id": "profile-a"}]}
                    ],
                ),
                _default_handler_yaml(
                    "xsoar-b",
                    capabilities=[
                        {"id": "cap-shared", "auth_options": [{"id": "profile-b"}]}
                    ],
                ),
            ],
        )
        handler_a = _get_handler(connector, "xsoar-a")
        handler_b = _get_handler(connector, "xsoar-b")

        ids_a = {f.raw_id for f in walk_visible_fields(connector, handler_a)}
        ids_b = {f.raw_id for f in walk_visible_fields(connector, handler_b)}

        assert "field_only_for_a" in ids_a
        assert "field_only_for_a" not in ids_b, (
            "Bug 1 regression: handler B saw handler A's view_group-scoped "
            "general_configurations field."
        )
        assert "field_only_for_b" in ids_b
        assert "field_only_for_b" not in ids_a

    def test_required_for_capabilities_scoping(self, tmp_path):
        """
        Given: a standard connector with a general_configurations group
               scoped via required_for_capabilities: [cap-a]. Two handlers:
               one subscribed to cap-a, one to cap-b.
        When: walk_visible_fields runs per handler.
        Then: only the cap-a-subscribing handler sees the gated field.
        """
        connector = _build_connector(
            tmp_path,
            capabilities={
                "metadata": {"title": "Capabilities"},
                "general_configurations": {
                    "configurations": [
                        {
                            "required_for_capabilities": ["cap-a"],
                            "fields": [{"id": "cap_a_only_field"}],
                        }
                    ]
                },
                "capabilities": [{"id": "cap-a"}, {"id": "cap-b"}],
            },
            handlers=[
                _default_handler_yaml(
                    "xsoar-a",
                    capabilities=[
                        {"id": "cap-a", "auth_options": [{"id": "default"}]}
                    ],
                ),
                _default_handler_yaml(
                    "xsoar-b",
                    capabilities=[
                        {"id": "cap-b", "auth_options": [{"id": "default"}]}
                    ],
                ),
            ],
        )
        handler_a = _get_handler(connector, "xsoar-a")
        handler_b = _get_handler(connector, "xsoar-b")

        ids_a = {f.raw_id for f in walk_visible_fields(connector, handler_a)}
        ids_b = {f.raw_id for f in walk_visible_fields(connector, handler_b)}

        assert "cap_a_only_field" in ids_a
        assert "cap_a_only_field" not in ids_b

    def test_no_scoping_marker_is_shared(self, tmp_path):
        """
        Given: a general_configurations group with neither view_group nor
               required_for_capabilities.
        When: walk_visible_fields runs for two handlers with disjoint
              caps / auth profiles.
        Then: BOTH handlers see the field (shared).
        """
        connector = _build_connector(
            tmp_path,
            capabilities={
                "metadata": {"title": "Capabilities"},
                "general_configurations": {
                    "configurations": [
                        {"fields": [{"id": "shared_field"}]},
                    ]
                },
                "capabilities": [{"id": "cap-a"}, {"id": "cap-b"}],
            },
            handlers=[
                _default_handler_yaml(
                    "xsoar-a",
                    capabilities=[
                        {"id": "cap-a", "auth_options": [{"id": "default"}]}
                    ],
                ),
                _default_handler_yaml(
                    "xsoar-b",
                    capabilities=[
                        {"id": "cap-b", "auth_options": [{"id": "default"}]}
                    ],
                ),
            ],
        )
        handler_a = _get_handler(connector, "xsoar-a")
        handler_b = _get_handler(connector, "xsoar-b")

        assert "shared_field" in {f.raw_id for f in walk_visible_fields(connector, handler_a)}
        assert "shared_field" in {f.raw_id for f in walk_visible_fields(connector, handler_b)}

    def test_both_markers_and_semantics(self, tmp_path):
        """
        Given: a general_configurations group with BOTH view_group AND
               required_for_capabilities set (authoring drift). Handler
               owns the view_group but NOT the required capability.
        When: walk_visible_fields runs.
        Then: field is INVISIBLE — the predicate ANDs the two markers.
              (Matches
              ``general_configurations_field_group_visible_for_handler``
              docstring.)
        """
        connector = _build_connector(
            tmp_path,
            grouped=True,
            connection={
                "metadata": {"title": "Connection"},
                "view_groups": [{"id": "vg-a"}],
                "general_configurations": {
                    "configurations": [
                        {
                            "view_group": "vg-a",
                            "required_for_capabilities": ["cap-required"],
                            "fields": [{"id": "gated_field"}],
                        }
                    ]
                },
                "profiles": [
                    {
                        "id": "profile-a",
                        "type": "plain",
                        "view_group": "vg-a",
                        "configurations": [],
                    }
                ],
            },
            capabilities={
                "metadata": {"title": "Capabilities"},
                "capabilities": [{"id": "cap-owned"}, {"id": "cap-required"}],
            },
            handlers=[
                # Handler owns vg-a but NOT cap-required (only cap-owned).
                _default_handler_yaml(
                    "xsoar-a",
                    capabilities=[
                        {"id": "cap-owned", "auth_options": [{"id": "profile-a"}]}
                    ],
                ),
            ],
        )
        handler = _get_handler(connector, "xsoar-a")
        ids = {f.raw_id for f in walk_visible_fields(connector, handler)}
        assert "gated_field" not in ids


# ============================================================
# Section 6 rows 9-10 — Grouped sub-cap direct-read (Bug 3)
# ============================================================


class TestGroupedSubCapabilityDirectRead:
    """Section 6 rows 9-10 + Bug 3 regression."""

    def test_grouped_sub_cap_entry_yielded(self, tmp_path):
        """
        Given: a grouped connector whose configurations.yaml
               ``configurations[]`` entry is keyed by a SUB-cap id
               (e.g. ``fetch-assets-and-vulnerabilities_tenable-sc``);
               handler subscribes to that sub-cap id verbatim.
        When: walk_visible_fields runs.
        Then: every field inside that entry appears in the result with
              origin == CONFIGURATIONS_CAPABILITY and capability_id ==
              the sub-cap id (bug-3 regression: parent-collapse would
              silently drop these).
        """
        connector = _build_connector(
            tmp_path,
            grouped=True,
            capabilities={
                "metadata": {"title": "Capabilities"},
                "capabilities": [
                    {
                        "id": "fetch-assets-and-vulnerabilities",
                        "sub_capabilities": [
                            {"id": "fetch-assets-and-vulnerabilities_tenable-sc"}
                        ],
                    }
                ],
            },
            configurations={
                "configurations": [
                    {
                        "id": "fetch-assets-and-vulnerabilities_tenable-sc",
                        "configurations": [
                            {
                                "fields": [
                                    {"id": "assetsFetchInterval"},
                                    {"id": "assetsMaxFetch"},
                                ]
                            }
                        ],
                    }
                ]
            },
            write_configurations=True,
            handlers=[
                _default_handler_yaml(
                    "xsoar-tenable-sc",
                    capabilities=[
                        {
                            "id": "fetch-assets-and-vulnerabilities_tenable-sc",
                            "auth_options": [{"id": "default"}],
                        }
                    ],
                )
            ],
        )
        handler = _get_handler(connector, "xsoar-tenable-sc")
        fields = walk_visible_fields(connector, handler)

        per_cap = [f for f in fields if f.origin == FieldOrigin.CONFIGURATIONS_CAPABILITY]
        assert {f.raw_id for f in per_cap} == {"assetsFetchInterval", "assetsMaxFetch"}, (
            "Bug 3 regression: sub-cap configurations[] entry was dropped."
        )
        for f in per_cap:
            assert f.capability_id == "fetch-assets-and-vulnerabilities_tenable-sc"
            assert f.parent_capability_id == "fetch-assets-and-vulnerabilities"

    def test_parent_subscription_does_not_leak_sub_cap_entry(self, tmp_path):
        """
        Given: same shape as above but handler subscribes ONLY to the
               parent ``fetch-assets-and-vulnerabilities``, not the
               sub-cap.
        When: walk_visible_fields runs.
        Then: the sub-cap entry is NOT in the result (handler doesn't own
              it). Confirms the walker matches on exact ids as authored
              (per HandlerData.capability_ids docstring — no expansion).
        """
        connector = _build_connector(
            tmp_path,
            grouped=True,
            capabilities={
                "metadata": {"title": "Capabilities"},
                "capabilities": [
                    {
                        "id": "fetch-assets-and-vulnerabilities",
                        "sub_capabilities": [
                            {"id": "fetch-assets-and-vulnerabilities_tenable-sc"}
                        ],
                    }
                ],
            },
            configurations={
                "configurations": [
                    {
                        "id": "fetch-assets-and-vulnerabilities_tenable-sc",
                        "configurations": [
                            {"fields": [{"id": "assetsFetchInterval"}]}
                        ],
                    }
                ]
            },
            write_configurations=True,
            handlers=[
                _default_handler_yaml(
                    "xsoar-parent-only",
                    capabilities=[
                        {
                            "id": "fetch-assets-and-vulnerabilities",
                            "auth_options": [{"id": "default"}],
                        }
                    ],
                )
            ],
        )
        handler = _get_handler(connector, "xsoar-parent-only")
        fields = walk_visible_fields(connector, handler)
        assert not any(f.raw_id == "assetsFetchInterval" for f in fields)


# ============================================================
# Section 6 rows 7-8 + 14 — Serializer rename
# ============================================================


class TestSerializerRename:
    """Section 6 rows 7, 8, 14."""

    def test_serializer_rename_present(self, tmp_path):
        """
        Given: a handler whose serializer.yaml maps
               ``xsoar-splunkpy-v2_integrationLogLevel`` ->
               ``integrationLogLevel``. That id lives in a
               general_configurations field group.
        When: walk_visible_fields runs.
        Then: raw_id != runtime_name and is_serialized == True.
        """
        connector = _build_connector(
            tmp_path,
            capabilities={
                "metadata": {"title": "Capabilities"},
                "general_configurations": {
                    "configurations": [
                        {
                            "fields": [
                                {"id": "xsoar-splunkpy-v2_integrationLogLevel"}
                            ]
                        }
                    ]
                },
                "capabilities": [{"id": "test-capability"}],
            },
            serializers={
                "xsoar-test": {
                    "field_mappings": [
                        {
                            "id": "xsoar-splunkpy-v2_integrationLogLevel",
                            "field_name": "integrationLogLevel",
                        }
                    ]
                }
            },
        )
        handler = _get_handler(connector, "xsoar-test")
        fields = walk_visible_fields(connector, handler)
        renamed = [
            f for f in fields if f.raw_id == "xsoar-splunkpy-v2_integrationLogLevel"
        ]
        assert len(renamed) == 1
        assert renamed[0].runtime_name == "integrationLogLevel"
        assert renamed[0].is_serialized is True

    def test_serializer_rename_absent(self, tmp_path):
        """
        Given: a handler with no serializer.yaml.
        When: walk_visible_fields runs.
        Then: raw_id == runtime_name and is_serialized == False for every
              field.
        """
        connector = _build_connector(
            tmp_path,
            capabilities={
                "metadata": {"title": "Capabilities"},
                "general_configurations": {
                    "configurations": [{"fields": [{"id": "unrenamed"}]}]
                },
                "capabilities": [{"id": "test-capability"}],
            },
        )
        handler = _get_handler(connector, "xsoar-test")
        for f in walk_visible_fields(connector, handler):
            assert f.raw_id == f.runtime_name
            assert f.is_serialized is False

    def test_namespaced_id_with_serializer_rename(self, tmp_path):
        """
        Given: a grouped connector with a namespaced raw id
               ``xsoar-akamai_engine`` that the serializer maps to
               ``engine``.
        When: walk_visible_fields runs.
        Then: both raw_id and runtime_name are populated correctly and
              is_serialized == True.
        """
        connector = _build_connector(
            tmp_path,
            grouped=True,
            connection={
                "metadata": {"title": "Connection"},
                "view_groups": [{"id": "vg-akamai"}],
                "profiles": [
                    {
                        "id": "akamai-default",
                        "type": "plain",
                        "view_group": "vg-akamai",
                        "configurations": [
                            {"fields": [{"id": "xsoar-akamai_engine"}]}
                        ],
                    }
                ],
            },
            capabilities={
                "metadata": {"title": "Capabilities"},
                "capabilities": [{"id": "cap-a"}],
            },
            handlers=[
                _default_handler_yaml(
                    "xsoar-akamai",
                    capabilities=[
                        {"id": "cap-a", "auth_options": [{"id": "akamai-default"}]}
                    ],
                )
            ],
            serializers={
                "xsoar-akamai": {
                    "field_mappings": [
                        {"id": "xsoar-akamai_engine", "field_name": "engine"}
                    ]
                }
            },
        )
        handler = _get_handler(connector, "xsoar-akamai")
        matches = [
            f
            for f in walk_visible_fields(connector, handler)
            if f.raw_id == "xsoar-akamai_engine"
        ]
        assert len(matches) == 1
        assert matches[0].runtime_name == "engine"
        assert matches[0].is_serialized is True


# ============================================================
# Section 6 row 15 — Same id in two sources (Q1 no-dedup)
# ============================================================


class TestNoDedup:
    """Section 6 row 15 + Q1 regression."""

    def test_same_field_id_in_two_sources_yields_two_entries(self, tmp_path):
        """
        Given: the same field id appears in capabilities.yaml
               general_configurations AND in configurations.yaml
               configurations[<cap>].
        When: walk_visible_fields runs.
        Then: TWO HandlerVisibleField entries with distinct origins and
              distinct source_file paths. Q1 no-dedup regression.
        """
        connector = _build_connector(
            tmp_path,
            capabilities={
                "metadata": {"title": "Capabilities"},
                "general_configurations": {
                    "configurations": [{"fields": [{"id": "duplicated_id"}]}]
                },
                "capabilities": [{"id": "test-capability"}],
            },
            configurations={
                "configurations": [
                    {
                        "id": "test-capability",
                        "configurations": [
                            {"fields": [{"id": "duplicated_id"}]}
                        ],
                    }
                ]
            },
            write_configurations=True,
        )
        handler = _get_handler(connector, "xsoar-test")
        matches = [
            f
            for f in walk_visible_fields(connector, handler)
            if f.raw_id == "duplicated_id"
        ]
        assert len(matches) == 2
        origins = {f.origin for f in matches}
        assert origins == {
            FieldOrigin.CAPABILITIES_GENERAL,
            FieldOrigin.CONFIGURATIONS_CAPABILITY,
        }
        source_files = {f.source_file for f in matches}
        assert len(source_files) == 2


# ============================================================
# Section 6 rows 11-13 — Handler-scoping (auth profiles, multi-handler)
# ============================================================


class TestHandlerScoping:
    """Section 6 rows 11-13."""

    def test_anonymous_handler_no_profile_fields(self, tmp_path):
        """
        Given: a handler with zero auth profiles.
        When: walk_visible_fields runs.
        Then: no CONNECTION_PROFILE-origin fields; other origins may or
              may not be present but must not crash.
        """
        connector = _build_connector(
            tmp_path,
            connection={
                "metadata": {"title": "Connection"},
                "profiles": [
                    {
                        "id": "default",
                        "type": "plain",
                        "configurations": [{"fields": [{"id": "profile_field"}]}],
                    }
                ],
            },
            handlers=[
                _default_handler_yaml(
                    "xsoar-anon",
                    capabilities=[{"id": "test-capability"}],  # no auth_options
                )
            ],
        )
        handler = _get_handler(connector, "xsoar-anon")
        fields = walk_visible_fields(connector, handler)
        assert not any(f.origin == FieldOrigin.CONNECTION_PROFILE for f in fields)

    def test_handler_with_multiple_auth_profiles(self, tmp_path):
        """
        Given: a handler auth-binding to two distinct profile ids.
        When: walk_visible_fields runs.
        Then: fields from BOTH profiles appear with correct profile_id
              attribution.
        """
        connector = _build_connector(
            tmp_path,
            connection={
                "metadata": {"title": "Connection"},
                "profiles": [
                    {
                        "id": "profile-1",
                        "type": "plain",
                        "configurations": [{"fields": [{"id": "field_p1"}]}],
                    },
                    {
                        "id": "profile-2",
                        "type": "plain",
                        "configurations": [{"fields": [{"id": "field_p2"}]}],
                    },
                ],
            },
            handlers=[
                _default_handler_yaml(
                    "xsoar-multi",
                    capabilities=[
                        {
                            "id": "test-capability",
                            "auth_options": [{"id": "profile-1"}, {"id": "profile-2"}],
                        }
                    ],
                )
            ],
        )
        handler = _get_handler(connector, "xsoar-multi")
        profile_fields = [
            f
            for f in walk_visible_fields(connector, handler)
            if f.origin == FieldOrigin.CONNECTION_PROFILE
        ]
        by_pid = {f.profile_id: f.raw_id for f in profile_fields}
        assert by_pid == {"profile-1": "field_p1", "profile-2": "field_p2"}

    def test_multi_handler_no_cross_contamination(self, tmp_path):
        """
        Given: two handlers with disjoint caps AND disjoint auth profiles.
        When: walk_visible_fields runs for each.
        Then: their per-cap and per-profile field sets are disjoint (no
              cross-contamination).
        """
        connector = _build_connector(
            tmp_path,
            grouped=True,
            connection={
                "metadata": {"title": "Connection"},
                "profiles": [
                    {
                        "id": "profile-a",
                        "type": "plain",
                        "configurations": [{"fields": [{"id": "field_pa"}]}],
                    },
                    {
                        "id": "profile-b",
                        "type": "plain",
                        "configurations": [{"fields": [{"id": "field_pb"}]}],
                    },
                ],
            },
            capabilities={
                "metadata": {"title": "Capabilities"},
                "capabilities": [{"id": "cap-a"}, {"id": "cap-b"}],
            },
            configurations={
                "configurations": [
                    {
                        "id": "cap-a",
                        "configurations": [{"fields": [{"id": "field_capa"}]}],
                    },
                    {
                        "id": "cap-b",
                        "configurations": [{"fields": [{"id": "field_capb"}]}],
                    },
                ]
            },
            write_configurations=True,
            handlers=[
                _default_handler_yaml(
                    "xsoar-a",
                    capabilities=[
                        {"id": "cap-a", "auth_options": [{"id": "profile-a"}]}
                    ],
                ),
                _default_handler_yaml(
                    "xsoar-b",
                    capabilities=[
                        {"id": "cap-b", "auth_options": [{"id": "profile-b"}]}
                    ],
                ),
            ],
        )
        handler_a = _get_handler(connector, "xsoar-a")
        handler_b = _get_handler(connector, "xsoar-b")
        ids_a = {f.raw_id for f in walk_visible_fields(connector, handler_a)}
        ids_b = {f.raw_id for f in walk_visible_fields(connector, handler_b)}

        # Cross-contamination check.
        assert "field_pa" in ids_a and "field_pa" not in ids_b
        assert "field_pb" in ids_b and "field_pb" not in ids_a
        assert "field_capa" in ids_a and "field_capa" not in ids_b
        assert "field_capb" in ids_b and "field_capb" not in ids_a


# ============================================================
# Section 6 rows 16-19 — Missing files / empty blocks (graceful)
# ============================================================


class TestGracefulHandling:
    """Section 6 rows 16-19 — walker must not crash on missing / empty
    sub-files, and must yield an empty list for that origin.
    """

    def test_missing_connection_yaml(self, tmp_path):
        """
        Given: a connector with no connection.yaml.
        When: walk_visible_fields runs.
        Then: no CONNECTION_* fields are emitted; other origins unaffected.
        """
        connector = _build_connector(
            tmp_path,
            write_connection=False,
            capabilities={
                "metadata": {"title": "Capabilities"},
                "general_configurations": {
                    "configurations": [{"fields": [{"id": "cap_field"}]}]
                },
                "capabilities": [{"id": "test-capability"}],
            },
        )
        handler = _get_handler(connector, "xsoar-test")
        fields = walk_visible_fields(connector, handler)
        origins = {f.origin for f in fields}
        assert FieldOrigin.CONNECTION_GENERAL not in origins
        assert FieldOrigin.CONNECTION_PROFILE not in origins
        assert FieldOrigin.CAPABILITIES_GENERAL in origins

    def test_missing_capabilities_general_configurations(self, tmp_path):
        """
        Given: capabilities.yaml exists but has no ``general_configurations``.
        When: walk_visible_fields runs.
        Then: no CAPABILITIES_GENERAL fields; no crash.
        """
        connector = _build_connector(
            tmp_path,
            capabilities={
                "metadata": {"title": "Capabilities"},
                "capabilities": [{"id": "test-capability"}],
            },
        )
        handler = _get_handler(connector, "xsoar-test")
        fields = walk_visible_fields(connector, handler)
        assert not any(f.origin == FieldOrigin.CAPABILITIES_GENERAL for f in fields)

    def test_missing_configurations_yaml(self, tmp_path):
        """
        Given: a standard connector with no configurations.yaml at all.
        When: walk_visible_fields runs.
        Then: no CONFIGURATIONS_* fields; no crash.
        """
        connector = _build_connector(
            tmp_path,
            write_configurations=False,
        )
        handler = _get_handler(connector, "xsoar-test")
        fields = walk_visible_fields(connector, handler)
        origins = {f.origin for f in fields}
        assert FieldOrigin.CONFIGURATIONS_GENERAL not in origins
        assert FieldOrigin.CONFIGURATIONS_CAPABILITY not in origins

    def test_empty_general_configurations(self, tmp_path):
        """
        Given: general_configurations block is present with an empty
               ``configurations: []`` list.
        When: walk_visible_fields runs.
        Then: no fields from that origin.
        """
        connector = _build_connector(
            tmp_path,
            capabilities={
                "metadata": {"title": "Capabilities"},
                "general_configurations": {"configurations": []},
                "capabilities": [{"id": "test-capability"}],
            },
        )
        handler = _get_handler(connector, "xsoar-test")
        fields = walk_visible_fields(connector, handler)
        assert not any(f.origin == FieldOrigin.CAPABILITIES_GENERAL for f in fields)


# ============================================================
# Public API — Connector.visible_* methods
# ============================================================


class TestConnectorPublicMethods:
    """The three thin methods delegating to walk_visible_fields."""

    def _minimal_connector(self, tmp_path):
        return _build_connector(
            tmp_path,
            connection={
                "metadata": {"title": "Connection"},
                "general_configurations": {
                    "configurations": [{"fields": [{"id": "shared_conn"}]}]
                },
                "profiles": [
                    {
                        "id": "default",
                        "type": "plain",
                        "configurations": [{"fields": [{"id": "profile_field"}]}],
                    }
                ],
            },
            capabilities={
                "metadata": {"title": "Capabilities"},
                "capabilities": [{"id": "test-capability"}],
            },
            configurations={
                "configurations": [
                    {
                        "id": "test-capability",
                        "configurations": [{"fields": [{"id": "cap_field"}]}],
                    }
                ]
            },
            write_configurations=True,
        )

    def test_visible_fields_for_handler_delegates(self, tmp_path):
        connector = self._minimal_connector(tmp_path)
        handler = _get_handler(connector, "xsoar-test")
        via_method = connector.visible_fields_for_handler(handler)
        via_fn = walk_visible_fields(connector, handler)
        assert [f.raw_id for f in via_method] == [f.raw_id for f in via_fn]
        assert [f.origin for f in via_method] == [f.origin for f in via_fn]

    def test_visible_field_by_runtime_name_first_hit(self, tmp_path):
        """When the same runtime name appears in two origins, first-hit
        in walker order is returned (§7 Q1 documented behaviour)."""
        connector = _build_connector(
            tmp_path,
            connection={
                "metadata": {"title": "Connection"},
                "general_configurations": {
                    "configurations": [{"fields": [{"id": "duplicated"}]}]
                },
                "profiles": [
                    {
                        "id": "default",
                        "type": "plain",
                        "configurations": [{"fields": [{"id": "duplicated"}]}],
                    }
                ],
            },
            capabilities={
                "metadata": {"title": "Capabilities"},
                "capabilities": [{"id": "test-capability"}],
            },
        )
        handler = _get_handler(connector, "xsoar-test")
        hit = connector.visible_field_for_handler_by_runtime_name(
            handler, "duplicated"
        )
        assert hit is not None
        assert hit.origin == FieldOrigin.CONNECTION_GENERAL

    def test_visible_field_by_runtime_name_returns_none_when_absent(self, tmp_path):
        connector = self._minimal_connector(tmp_path)
        handler = _get_handler(connector, "xsoar-test")
        assert (
            connector.visible_field_for_handler_by_runtime_name(handler, "no_such_id")
            is None
        )

    def test_visible_field_by_runtime_name_matches_post_serializer(self, tmp_path):
        """Lookup key is the post-serializer runtime name, not the raw id."""
        connector = _build_connector(
            tmp_path,
            capabilities={
                "metadata": {"title": "Capabilities"},
                "general_configurations": {
                    "configurations": [{"fields": [{"id": "raw_only"}]}]
                },
                "capabilities": [{"id": "test-capability"}],
            },
            serializers={
                "xsoar-test": {
                    "field_mappings": [
                        {"id": "raw_only", "field_name": "runtime_name"}
                    ]
                }
            },
        )
        handler = _get_handler(connector, "xsoar-test")
        # Raw id must NOT match — only runtime name does.
        assert (
            connector.visible_field_for_handler_by_runtime_name(handler, "raw_only")
            is None
        )
        hit = connector.visible_field_for_handler_by_runtime_name(
            handler, "runtime_name"
        )
        assert hit is not None
        assert hit.raw_id == "raw_only"
        assert hit.is_serialized is True

    def test_visible_fields_for_handler_by_origin(self, tmp_path):
        connector = self._minimal_connector(tmp_path)
        handler = _get_handler(connector, "xsoar-test")
        general = connector.visible_fields_for_handler_by_origin(
            handler, FieldOrigin.CONNECTION_GENERAL
        )
        assert [f.raw_id for f in general] == ["shared_conn"]
        per_cap = connector.visible_fields_for_handler_by_origin(
            handler, FieldOrigin.CONFIGURATIONS_CAPABILITY
        )
        assert [f.raw_id for f in per_cap] == ["cap_field"]


# ============================================================
# Sidecar / invariants (Q2 raw_dict, Bug 4 source_file, non-XSOAR handler)
# ============================================================


class TestInvariants:
    def test_raw_dict_populated_on_every_field(self, tmp_path):
        """Q2 regression: every HandlerVisibleField carries a non-None
        ``raw_dict`` sidecar."""
        connector = _build_connector(
            tmp_path,
            connection={
                "metadata": {"title": "Connection"},
                "general_configurations": {
                    "configurations": [{"fields": [{"id": "gen"}]}]
                },
                "profiles": [
                    {
                        "id": "default",
                        "type": "plain",
                        "configurations": [{"fields": [{"id": "prof"}]}],
                    }
                ],
            },
            capabilities={
                "metadata": {"title": "Capabilities"},
                "general_configurations": {
                    "configurations": [{"fields": [{"id": "caps"}]}]
                },
                "capabilities": [{"id": "test-capability"}],
            },
            configurations={
                "general_configurations": {
                    "configurations": [{"fields": [{"id": "cfg_gen"}]}]
                },
                "configurations": [
                    {
                        "id": "test-capability",
                        "configurations": [{"fields": [{"id": "cap"}]}],
                    }
                ],
            },
            write_configurations=True,
        )
        handler = _get_handler(connector, "xsoar-test")
        fields = walk_visible_fields(connector, handler)
        for f in fields:
            assert f.raw_dict is not None, f"raw_dict missing on {f.raw_id!r}"
            # And it must at least round-trip the id.
            assert f.raw_dict.get("id") == f.raw_id

    def test_source_file_is_absolute_path(self, tmp_path):
        """Bug 4 regression: source_file is always an absolute :class:`Path`,
        never a bare filename string like ``"connection.yaml"``."""
        connector = _build_connector(
            tmp_path,
            connection={
                "metadata": {"title": "Connection"},
                "general_configurations": {
                    "configurations": [{"fields": [{"id": "gen"}]}]
                },
                "profiles": [
                    {
                        "id": "default",
                        "type": "plain",
                        "configurations": [{"fields": [{"id": "prof"}]}],
                    }
                ],
            },
            capabilities={
                "metadata": {"title": "Capabilities"},
                "general_configurations": {
                    "configurations": [{"fields": [{"id": "caps"}]}]
                },
                "capabilities": [{"id": "test-capability"}],
            },
            configurations={
                "configurations": [
                    {
                        "id": "test-capability",
                        "configurations": [{"fields": [{"id": "cap"}]}],
                    }
                ]
            },
            write_configurations=True,
        )
        handler = _get_handler(connector, "xsoar-test")
        fields = walk_visible_fields(connector, handler)
        assert fields, "Sanity: expected at least one visible field"
        for f in fields:
            assert isinstance(f.source_file, Path), (
                f"source_file must be a Path, got {type(f.source_file).__name__} "
                f"for {f.raw_id!r}"
            )
            assert f.source_file.is_absolute(), (
                f"Bug 4 regression: source_file must be absolute, got "
                f"{f.source_file!r} for {f.raw_id!r}"
            )
            # And the file it points at must actually exist on disk.
            assert f.source_file.exists(), (
                f"source_file {f.source_file!r} for {f.raw_id!r} does not exist"
            )

    def test_non_xsoar_handler_still_walks(self, tmp_path):
        """Section 6 row 21: the walker is NOT xsoar-gated. Whether to
        skip non-xsoar handlers is a per-validator decision, not a
        walker concern.
        """
        connector = _build_connector(
            tmp_path,
            capabilities={
                "metadata": {"title": "Capabilities"},
                "general_configurations": {
                    "configurations": [{"fields": [{"id": "gen"}]}]
                },
                "capabilities": [{"id": "test-capability"}],
            },
            handlers=[
                _default_handler_yaml("other-handler", module="other"),
            ],
        )
        handler = _get_handler(connector, "other-handler")
        fields = walk_visible_fields(connector, handler)
        assert any(f.raw_id == "gen" for f in fields), (
            "Non-XSOAR handler still expects a walker result; skipping is a "
            "validator decision, not a walker one."
        )


class TestConnectionWalkerRawYAMLOnly:
    """Phase 4a walker-unification regression.

    Guards the exact class of test breakage Phase 3 (CO138 / CO141
    migrations) hit: mutating ``connection_file.file_content`` — the raw
    YAML dict — without also refreshing the parsed
    :attr:`Connector.connection` pydantic sub-model. Before the
    unification, ``_walk_connection_general`` and
    ``_walk_connection_profiles`` read ``connector.connection`` (parsed),
    silently ignoring raw-YAML edits, so every Phase 3 test that seeded
    fields via ``file_content`` alone had to hand-refresh the parsed
    model. The unified walkers now read raw YAML directly and this test
    pins that behaviour so a future re-regression is caught in the
    walker's own suite instead of surfacing as spooky validator failures.
    """

    def test_connection_profiles_seeded_only_via_file_content_are_visible(
        self, tmp_path
    ):
        """Seed profile fields ONLY via ``connection_file.file_content``
        (after the parsed :attr:`Connector.connection` was frozen with an
        empty profiles list) and assert the walker still yields them.
        """
        # Build a connector whose parsed connection.profiles is EMPTY
        # (only general_configurations authored at parse time).
        connector = _build_connector(
            tmp_path,
            connection={
                "metadata": {"title": "Connection"},
                "general_configurations": {
                    "configurations": [{"fields": [{"id": "shared_url"}]}]
                },
                "profiles": [],
            },
            handlers=[
                _default_handler_yaml(
                    "xsoar-test",
                    capabilities=[
                        {
                            "id": "test-capability",
                            "auth_options": [{"id": "basic.default"}],
                        }
                    ],
                )
            ],
        )
        handler = _get_handler(connector, "xsoar-test")

        # Sanity: parsed model has no profiles - walker must not rely on
        # it after this point.
        assert connector.connection is not None
        assert connector.connection.profiles == []

        # Splice a profile in via the raw YAML sidecar only. This is the
        # exact pattern Phase 3 tests used to seed extra fields via
        # in-memory YAML edits.
        connector.connection_file.file_content["profiles"] = [
            {
                "id": "basic.default",
                "type": "plain",
                "configurations": [
                    {"fields": [{"id": "username"}, {"id": "password"}]}
                ],
            }
        ]

        # Clear the walker cache so the next call re-walks (validate
        # runs never mutate connectors after parse, but tests do).
        try:
            del connector._visible_fields_cache
        except AttributeError:
            pass

        fields = walk_visible_fields(connector, handler)
        raw_ids = {f.raw_id for f in fields}
        assert "username" in raw_ids, (
            "Raw-YAML-only profile seed must produce a walker entry; "
            f"got {sorted(raw_ids)!r}"
        )
        assert "password" in raw_ids, (
            "Raw-YAML-only profile seed must produce a walker entry; "
            f"got {sorted(raw_ids)!r}"
        )

        profile_fields = [
            f for f in fields if f.origin == FieldOrigin.CONNECTION_PROFILE
        ]
        assert {f.profile_id for f in profile_fields} == {"basic.default"}, (
            "profile_id must be populated from the raw-YAML profile "
            "block, not the (empty) parsed model"
        )

    def test_connection_general_seeded_only_via_file_content_is_visible(
        self, tmp_path
    ):
        """Same regression, for the general_configurations branch. Seed
        an extra field group via raw YAML after parse and assert the
        walker sees it.
        """
        connector = _build_connector(
            tmp_path,
            connection={
                "metadata": {"title": "Connection"},
                "general_configurations": {"configurations": []},
                "profiles": [],
            },
        )
        handler = _get_handler(connector, "xsoar-test")

        assert connector.connection is not None
        assert connector.connection.general_configurations is not None
        assert (
            connector.connection.general_configurations.configurations == []
        )

        # Splice a general_configurations field group in via raw YAML.
        connector.connection_file.file_content["general_configurations"] = {
            "configurations": [
                {"fields": [{"id": "api_url"}, {"id": "verify_ssl"}]}
            ]
        }

        try:
            del connector._visible_fields_cache
        except AttributeError:
            pass

        fields = walk_visible_fields(connector, handler)
        general_ids = {
            f.raw_id
            for f in fields
            if f.origin == FieldOrigin.CONNECTION_GENERAL
        }
        assert general_ids == {"api_url", "verify_ssl"}, (
            "Raw-YAML-only general_configurations seed must be visible "
            f"to the walker; got {sorted(general_ids)!r}"
        )


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-x", "-v"])
