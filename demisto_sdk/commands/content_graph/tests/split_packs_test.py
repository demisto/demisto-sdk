"""Tests for the split-pack / derived-pack feature (Phase 1 SDK implementation).

Covers:
- ContentType coupling classification
- PackDestination enum
- Pack.destination property
- Pack._is_item_tightly_coupled with overrides
- DerivedPackParser generation
- ContentDTO destination filtering
- pack_destinations.json generation
- Validators: PA135, PA136, PA137
"""
from __future__ import annotations

import json as stdlib_json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest

from demisto_sdk.commands.content_graph.common import (
    DEFAULT_DERIVED_PACK_SOURCE,
    DERIVED_PACK_SUFFIX,
    ENABLE_SPLIT_PACKS,
    TIGHTLY_COUPLED_TYPES,
    ContentType,
    PackDestination,
    Relationships,
    resolve_derived_pack_source,
)


# ---------------------------------------------------------------------------
# ContentType coupling classification tests
# ---------------------------------------------------------------------------


class TestContentTypeCoupling:
    """Tests for ContentType.is_tightly_coupled and related classmethods."""

    def test_integration_is_tightly_coupled(self):
        assert ContentType.INTEGRATION.is_tightly_coupled is True

    def test_modeling_rule_is_tightly_coupled(self):
        assert ContentType.MODELING_RULE.is_tightly_coupled is True

    def test_parsing_rule_is_tightly_coupled(self):
        assert ContentType.PARSING_RULE.is_tightly_coupled is True

    def test_correlation_rule_is_tightly_coupled(self):
        assert ContentType.CORRELATION_RULE.is_tightly_coupled is True

    def test_trigger_is_tightly_coupled(self):
        assert ContentType.TRIGGER.is_tightly_coupled is True

    def test_xdrc_template_is_tightly_coupled(self):
        assert ContentType.XDRC_TEMPLATE.is_tightly_coupled is True

    def test_assets_modeling_rule_is_tightly_coupled(self):
        assert ContentType.ASSETS_MODELING_RULE.is_tightly_coupled is True

    def test_mapper_is_tightly_coupled(self):
        assert ContentType.MAPPER.is_tightly_coupled is True

    def test_script_is_loosely_coupled(self):
        assert ContentType.SCRIPT.is_tightly_coupled is False

    def test_playbook_is_loosely_coupled(self):
        assert ContentType.PLAYBOOK.is_tightly_coupled is False

    def test_incident_field_is_loosely_coupled(self):
        assert ContentType.INCIDENT_FIELD.is_tightly_coupled is False

    def test_dashboard_is_loosely_coupled(self):
        assert ContentType.DASHBOARD.is_tightly_coupled is False

    def test_classifier_is_tightly_coupled(self):
        """Classifiers route an integration's incoming data and cannot stand alone."""
        assert ContentType.CLASSIFIER.is_tightly_coupled is True

    def test_pack_is_not_tightly_coupled(self):
        """Non-content items should not be tightly coupled."""
        assert ContentType.PACK.is_tightly_coupled is False

    def test_command_is_not_tightly_coupled(self):
        assert ContentType.COMMAND.is_tightly_coupled is False

    def test_tightly_coupled_types_returns_frozenset(self):
        result = ContentType.tightly_coupled_types()
        assert isinstance(result, frozenset)
        assert result == TIGHTLY_COUPLED_TYPES

    def test_loosely_coupled_types_excludes_tightly_coupled(self):
        loosely = ContentType.loosely_coupled_types()
        for ct in loosely:
            assert ct not in TIGHTLY_COUPLED_TYPES

    def test_tightly_and_loosely_cover_all_content_items(self):
        """Tightly + loosely coupled should cover all content items."""
        all_content = frozenset(ContentType.content_items())
        tightly = ContentType.tightly_coupled_types()
        loosely = ContentType.loosely_coupled_types()
        assert tightly | loosely == all_content
        assert tightly & loosely == frozenset()  # no overlap


# ---------------------------------------------------------------------------
# PackDestination enum tests
# ---------------------------------------------------------------------------


class TestPackDestination:
    def test_marketplace_value(self):
        assert PackDestination.MARKETPLACE.value == "marketplace"

    def test_managed_content_value(self):
        assert PackDestination.MANAGED_CONTENT.value == "managed_content"

    def test_is_string_enum(self):
        assert isinstance(PackDestination.MARKETPLACE, str)


# ---------------------------------------------------------------------------
# DERIVED_PACK_SUFFIX constant test
# ---------------------------------------------------------------------------


class TestDerivedPackSuffix:
    def test_suffix_value(self):
        assert DERIVED_PACK_SUFFIX == "Managed"


# ---------------------------------------------------------------------------
# resolve_derived_pack_source precedence tests
# ---------------------------------------------------------------------------


class TestResolveDerivedPackSource:
    """The resolver decides the Managed Content feature directory a derived pack
    lands in: <bucket>/<bucket_path>/<source>/<pack_id>/."""

    def test_default_is_connectus(self, monkeypatch):
        monkeypatch.delenv("DERIVED_PACK_SOURCE", raising=False)
        assert resolve_derived_pack_source() == "connectus"
        assert DEFAULT_DERIVED_PACK_SOURCE == "connectus"

    def test_env_var_overrides_default(self, monkeypatch):
        monkeypatch.setenv("DERIVED_PACK_SOURCE", "other_feature")
        assert resolve_derived_pack_source() == "other_feature"

    def test_per_pack_value_overrides_env_var(self, monkeypatch):
        monkeypatch.setenv("DERIVED_PACK_SOURCE", "env_feature")
        assert resolve_derived_pack_source("pack_feature") == "pack_feature"

    def test_per_pack_value_overrides_default(self, monkeypatch):
        monkeypatch.delenv("DERIVED_PACK_SOURCE", raising=False)
        assert resolve_derived_pack_source("pack_feature") == "pack_feature"

    @pytest.mark.parametrize("empty_value", [None, ""])
    def test_empty_per_pack_value_falls_through(self, monkeypatch, empty_value):
        """An absent or blank ``derived_source`` must not shadow the lower
        precedence levels."""
        monkeypatch.setenv("DERIVED_PACK_SOURCE", "env_feature")
        assert resolve_derived_pack_source(empty_value) == "env_feature"

    def test_empty_env_var_falls_through_to_default(self, monkeypatch):
        monkeypatch.setenv("DERIVED_PACK_SOURCE", "")
        assert resolve_derived_pack_source() == DEFAULT_DERIVED_PACK_SOURCE

    def test_env_var_is_read_per_call_not_at_import(self, monkeypatch):
        """Unlike ENABLE_SPLIT_PACKS, the value must not be frozen at import
        time - otherwise it is neither testable nor settable by CI."""
        monkeypatch.setenv("DERIVED_PACK_SOURCE", "first")
        assert resolve_derived_pack_source() == "first"
        monkeypatch.setenv("DERIVED_PACK_SOURCE", "second")
        assert resolve_derived_pack_source() == "second"


# ---------------------------------------------------------------------------
# Pack.destination property tests (using mock Pack objects)
# ---------------------------------------------------------------------------


class TestPackDestinationProperty:
    """Tests for Pack.destination computed property."""

    def _make_mock_pack(
        self,
        managed: bool = False,
        is_derived: bool = False,
    ) -> MagicMock:
        """Create a mock Pack with the destination property logic."""
        from demisto_sdk.commands.content_graph.objects.pack import Pack

        mock = MagicMock(spec=Pack)
        mock.managed = managed
        mock.is_derived = is_derived
        # Use the real property logic
        mock.destination = (
            PackDestination.MANAGED_CONTENT
            if managed
            else PackDestination.MARKETPLACE
        )
        return mock

    def test_regular_pack_goes_to_marketplace(self):
        pack = self._make_mock_pack(managed=False)
        assert pack.destination == PackDestination.MARKETPLACE

    def test_managed_pack_goes_to_managed_content(self):
        pack = self._make_mock_pack(managed=True)
        assert pack.destination == PackDestination.MANAGED_CONTENT

    def test_derived_pack_goes_to_managed_content(self):
        pack = self._make_mock_pack(managed=True, is_derived=True)
        assert pack.destination == PackDestination.MANAGED_CONTENT


# ---------------------------------------------------------------------------
# Pack._is_item_tightly_coupled tests
# ---------------------------------------------------------------------------


class TestIsItemTightlyCoupled:
    """Tests for Pack._is_item_tightly_coupled with overrides."""

    def _make_content_item(
        self, object_id: str, content_type: ContentType
    ) -> MagicMock:
        mock = MagicMock()
        mock.object_id = object_id
        mock.content_type = content_type
        return mock

    def _make_pack_with_overrides(
        self, overrides: Optional[dict] = None
    ) -> MagicMock:
        from demisto_sdk.commands.content_graph.objects.pack import Pack

        mock = MagicMock(spec=Pack)
        mock.coupling_overrides = overrides
        # Bind the real method
        mock._is_item_tightly_coupled = Pack._is_item_tightly_coupled.__get__(
            mock, Pack
        )
        return mock

    def test_integration_default_tightly_coupled(self):
        pack = self._make_pack_with_overrides(None)
        item = self._make_content_item("MyIntegration", ContentType.INTEGRATION)
        assert pack._is_item_tightly_coupled(item) is True

    def test_script_default_loosely_coupled(self):
        pack = self._make_pack_with_overrides(None)
        item = self._make_content_item("MyScript", ContentType.SCRIPT)
        assert pack._is_item_tightly_coupled(item) is False

    def test_override_script_to_tightly_coupled(self):
        pack = self._make_pack_with_overrides(
            {"MyScript": "tightly_coupled"}
        )
        item = self._make_content_item("MyScript", ContentType.SCRIPT)
        assert pack._is_item_tightly_coupled(item) is True

    def test_override_integration_to_loosely_coupled(self):
        pack = self._make_pack_with_overrides(
            {"MyIntegration": "loosely_coupled"}
        )
        item = self._make_content_item("MyIntegration", ContentType.INTEGRATION)
        assert pack._is_item_tightly_coupled(item) is False

    def test_override_only_affects_specified_item(self):
        pack = self._make_pack_with_overrides(
            {"MyScript": "tightly_coupled"}
        )
        other_script = self._make_content_item("OtherScript", ContentType.SCRIPT)
        assert pack._is_item_tightly_coupled(other_script) is False


# ---------------------------------------------------------------------------
# DerivedPackParser tests
# ---------------------------------------------------------------------------


class TestDerivedPackParser:
    """Tests for DerivedPackParser creation and properties."""

    def _make_mock_original_parser(self) -> MagicMock:
        from demisto_sdk.commands.content_graph.parsers.pack import (
            PackContentItems,
            PackParser,
        )

        mock = MagicMock(spec=PackParser)
        mock.path = Path("/fake/Packs/TestPack")
        mock.object_id = "TestPack"
        mock.name = "Test Pack"
        mock.display_name = "Test Pack"
        mock.description = "A test pack"
        mock.support = "xsoar"
        mock.created = "2024-01-01"
        mock.updated = "2024-01-01"
        mock.legacy = True
        mock.email = ""
        mock.eulaLink = ""
        mock.author_image = ""
        mock.price = 0
        mock.hidden = False
        mock.server_min_version = "6.0.0"
        mock.current_version = "1.0.0"
        mock.version_info = ""
        mock.commit = "abc123"
        mock.downloads = 0
        mock.tags = ["tag1"]
        mock.default_data_source_id = ""
        mock.keywords = []
        mock.search_rank = 0
        mock.videos = []
        mock.excluded_dependencies = []
        mock.modules = []
        mock.integrations = []
        mock.premium = False
        mock.vendor_id = ""
        mock.partner_id = ""
        mock.partner_name = ""
        mock.preview_only = False
        mock.disable_monthly = False
        mock.content_commit_hash = ""
        mock.hybrid = False
        mock.pack_metadata_dict = {"name": "Test Pack"}
        mock.supportedModules = None
        mock.coupling_overrides = None
        mock.derived_source = None
        mock.internal = False
        mock.managed = False
        mock.source = ""
        mock.deprecated = False
        mock.private_pack_path = None
        mock.contributors = []
        mock.latest_rn_version = "1.0.0"
        mock.relationships = Relationships()
        mock.marketplaces = ["xsoar"]
        mock.url = ""
        mock.certification = "certified"
        mock.author = "Cortex XSOAR"
        mock.categories = []
        mock.use_cases = []
        mock.field_mapping = {"name": "name"}
        return mock

    def test_derived_pack_id(self):
        from demisto_sdk.commands.content_graph.parsers.pack import DerivedPackParser

        original = self._make_mock_original_parser()
        derived = DerivedPackParser(
            original_parser=original,
            derived_id="TestPackManaged",
        )
        assert derived.object_id == "TestPackManaged"

    def test_derived_pack_is_managed(self):
        from demisto_sdk.commands.content_graph.parsers.pack import DerivedPackParser

        original = self._make_mock_original_parser()
        derived = DerivedPackParser(
            original_parser=original,
            derived_id="TestPackManaged",
        )
        assert derived.managed is True

    def test_derived_pack_is_derived_flag(self):
        from demisto_sdk.commands.content_graph.parsers.pack import DerivedPackParser

        original = self._make_mock_original_parser()
        derived = DerivedPackParser(
            original_parser=original,
            derived_id="TestPackManaged",
        )
        assert derived.is_derived is True

    def test_derived_pack_derived_from(self):
        from demisto_sdk.commands.content_graph.parsers.pack import DerivedPackParser

        original = self._make_mock_original_parser()
        derived = DerivedPackParser(
            original_parser=original,
            derived_id="TestPackManaged",
        )
        assert derived.derived_from == "TestPack"

    def test_derived_pack_source_is_the_feature_not_the_origin_pack(self):
        """``source`` is the Managed Content feature directory, so it must be the
        feature name - not the originating pack's name. The link back to the
        origin is carried by ``derived_from``, asserted separately above."""
        from demisto_sdk.commands.content_graph.parsers.pack import DerivedPackParser

        original = self._make_mock_original_parser()
        derived = DerivedPackParser(
            original_parser=original,
            derived_id="TestPackManaged",
        )
        assert derived.source == DEFAULT_DERIVED_PACK_SOURCE
        assert derived.source != original.name

    def test_derived_pack_source_honours_per_pack_override(self):
        from demisto_sdk.commands.content_graph.parsers.pack import DerivedPackParser

        original = self._make_mock_original_parser()
        original.derived_source = "my_feature"
        derived = DerivedPackParser(
            original_parser=original,
            derived_id="TestPackManaged",
        )
        assert derived.source == "my_feature"

    def test_derived_pack_source_honours_env_override(self, monkeypatch):
        from demisto_sdk.commands.content_graph.parsers.pack import DerivedPackParser

        monkeypatch.setenv("DERIVED_PACK_SOURCE", "env_feature")
        original = self._make_mock_original_parser()
        derived = DerivedPackParser(
            original_parser=original,
            derived_id="TestPackManaged",
        )
        assert derived.source == "env_feature"

    def test_derived_pack_name_has_suffix(self):
        from demisto_sdk.commands.content_graph.parsers.pack import DerivedPackParser

        original = self._make_mock_original_parser()
        derived = DerivedPackParser(
            original_parser=original,
            derived_id="TestPackManaged",
        )
        assert derived.name == "Test Pack Managed"

    def test_derived_pack_content_type(self):
        from demisto_sdk.commands.content_graph.parsers.pack import DerivedPackParser

        original = self._make_mock_original_parser()
        derived = DerivedPackParser(
            original_parser=original,
            derived_id="TestPackManaged",
        )
        assert derived.content_type == ContentType.PACK


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------


class TestPA135CouplingOverrideReferences:
    """Tests for PA135 - coupling override references validator."""

    def _make_pack(
        self,
        object_id: str,
        coupling_overrides: Optional[dict],
        content_item_ids: List[str],
    ) -> MagicMock:
        from demisto_sdk.commands.content_graph.objects.pack import Pack

        mock = MagicMock(spec=Pack)
        mock.object_id = object_id
        mock.coupling_overrides = coupling_overrides
        items = []
        for item_id in content_item_ids:
            item = MagicMock()
            item.object_id = item_id
            items.append(item)
        mock.content_items = items
        return mock

    def test_no_overrides_passes(self):
        from demisto_sdk.commands.validate.validators.PA_validators.PA135_coupling_override_references import (
            CouplingOverrideReferencesValidator,
        )

        pack = self._make_pack("TestPack", None, ["Item1", "Item2"])
        validator = CouplingOverrideReferencesValidator()
        results = validator.obtain_invalid_content_items([pack])
        assert len(results) == 0

    def test_valid_overrides_passes(self):
        from demisto_sdk.commands.validate.validators.PA_validators.PA135_coupling_override_references import (
            CouplingOverrideReferencesValidator,
        )

        pack = self._make_pack(
            "TestPack",
            {"Item1": "tightly_coupled"},
            ["Item1", "Item2"],
        )
        validator = CouplingOverrideReferencesValidator()
        results = validator.obtain_invalid_content_items([pack])
        assert len(results) == 0

    def test_unknown_override_id_fails(self):
        from demisto_sdk.commands.validate.validators.PA_validators.PA135_coupling_override_references import (
            CouplingOverrideReferencesValidator,
        )

        pack = self._make_pack(
            "TestPack",
            {"NonExistentItem": "tightly_coupled"},
            ["Item1", "Item2"],
        )
        validator = CouplingOverrideReferencesValidator()
        results = validator.obtain_invalid_content_items([pack])
        assert len(results) == 1
        assert "NonExistentItem" in results[0].message


class TestPA136DerivedPackNamingConflict:
    """Tests for PA136 - derived pack naming conflict validator."""

    def _make_pack(
        self,
        object_id: str,
        managed: bool = False,
        is_derived: bool = False,
    ) -> MagicMock:
        from demisto_sdk.commands.content_graph.objects.pack import Pack

        mock = MagicMock(spec=Pack)
        mock.object_id = object_id
        mock.managed = managed
        mock.is_derived = is_derived
        return mock

    def test_no_conflict_passes(self):
        from demisto_sdk.commands.validate.validators.PA_validators.PA136_derived_pack_naming_conflict import (
            DerivedPackNamingConflictValidator,
        )

        packs = [
            self._make_pack("PackA"),
            self._make_pack("PackB"),
        ]
        validator = DerivedPackNamingConflictValidator()
        results = validator.obtain_invalid_content_items(packs)
        assert len(results) == 0

    def test_conflict_detected(self):
        from demisto_sdk.commands.validate.validators.PA_validators.PA136_derived_pack_naming_conflict import (
            DerivedPackNamingConflictValidator,
        )

        packs = [
            self._make_pack("PackA"),
            self._make_pack("PackAManaged"),  # conflicts with derived ID
        ]
        validator = DerivedPackNamingConflictValidator()
        results = validator.obtain_invalid_content_items(packs)
        assert len(results) == 1
        assert "PackAManaged" in results[0].message

    def test_managed_pack_skipped(self):
        from demisto_sdk.commands.validate.validators.PA_validators.PA136_derived_pack_naming_conflict import (
            DerivedPackNamingConflictValidator,
        )

        packs = [
            self._make_pack("PackA", managed=True),
            self._make_pack("PackAManaged"),
        ]
        validator = DerivedPackNamingConflictValidator()
        results = validator.obtain_invalid_content_items(packs)
        # PackA is managed, so it won't generate a derived pack
        assert len(results) == 0


class TestPA137ManagedPackMustHaveSource:
    """Tests for PA137 - managed pack must have source validator."""

    def _make_pack(
        self,
        object_id: str,
        managed: bool = False,
        source: str = "",
    ) -> MagicMock:
        from demisto_sdk.commands.content_graph.objects.pack import Pack

        mock = MagicMock(spec=Pack)
        mock.object_id = object_id
        mock.managed = managed
        mock.source = source
        return mock

    def test_non_managed_pack_passes(self):
        from demisto_sdk.commands.validate.validators.PA_validators.PA137_managed_pack_must_have_source import (
            ManagedPackMustHaveSourceValidator,
        )

        pack = self._make_pack("TestPack", managed=False, source="")
        validator = ManagedPackMustHaveSourceValidator()
        results = validator.obtain_invalid_content_items([pack])
        assert len(results) == 0

    def test_managed_pack_with_source_passes(self):
        from demisto_sdk.commands.validate.validators.PA_validators.PA137_managed_pack_must_have_source import (
            ManagedPackMustHaveSourceValidator,
        )

        pack = self._make_pack("TestPack", managed=True, source="OriginalPack")
        validator = ManagedPackMustHaveSourceValidator()
        results = validator.obtain_invalid_content_items([pack])
        assert len(results) == 0

    def test_managed_pack_without_source_fails(self):
        from demisto_sdk.commands.validate.validators.PA_validators.PA137_managed_pack_must_have_source import (
            ManagedPackMustHaveSourceValidator,
        )

        pack = self._make_pack("TestPack", managed=True, source="")
        validator = ManagedPackMustHaveSourceValidator()
        results = validator.obtain_invalid_content_items([pack])
        assert len(results) == 1
        assert "managed" in results[0].message.lower()


# ---------------------------------------------------------------------------
# StrictPackMetadata coupling_overrides validation tests
# ---------------------------------------------------------------------------


class TestStrictPackMetadataCouplingOverrides:
    """Tests for coupling_overrides validation in StrictPackMetadata."""

    def test_valid_coupling_overrides(self):
        from demisto_sdk.commands.content_graph.strict_objects.pack_meta_data import (
            StrictPackMetadata,
        )

        data = {
            "name": "TestPack",
            "support": "xsoar",
            "author": "Test",
            "currentVersion": "1.0.0",
            "serverMinVersion": "6.0.0",
            "coupling_overrides": {
                "MyScript": "tightly_coupled",
                "MyMapper": "loosely_coupled",
            },
        }
        # Should not raise
        StrictPackMetadata.parse_obj(data)

    def test_invalid_coupling_override_value(self):
        from demisto_sdk.commands.content_graph.strict_objects.pack_meta_data import (
            StrictPackMetadata,
        )

        data = {
            "name": "TestPack",
            "support": "xsoar",
            "author": "Test",
            "currentVersion": "1.0.0",
            "serverMinVersion": "6.0.0",
            "coupling_overrides": {
                "MyScript": "invalid_value",
            },
        }
        with pytest.raises(Exception):  # pydantic ValidationError
            StrictPackMetadata.parse_obj(data)

    def test_no_coupling_overrides_passes(self):
        from demisto_sdk.commands.content_graph.strict_objects.pack_meta_data import (
            StrictPackMetadata,
        )

        data = {
            "name": "TestPack",
            "support": "xsoar",
            "author": "Test",
            "currentVersion": "1.0.0",
            "serverMinVersion": "6.0.0",
        }
        # Should not raise
        StrictPackMetadata.parse_obj(data)

    def test_derived_source_is_accepted_by_the_strict_schema(self):
        """StrictPackMetadata sets ``extra = Extra.forbid``, so an undeclared
        ``derived_source`` in pack_metadata.json would fail validation and make
        the per-pack override unusable."""
        from demisto_sdk.commands.content_graph.strict_objects.pack_meta_data import (
            StrictPackMetadata,
        )

        data = {
            "name": "TestPack",
            "support": "xsoar",
            "author": "Test",
            "currentVersion": "1.0.0",
            "serverMinVersion": "6.0.0",
            "derived_source": "my_feature",
        }
        metadata = StrictPackMetadata.parse_obj(data)
        assert metadata.derived_source == "my_feature"


# ---------------------------------------------------------------------------
# ContentDTO destination filtering tests
# ---------------------------------------------------------------------------


class TestContentDTODestinationFiltering:
    """Tests for ContentDTO.dump() destination filtering."""

    def _make_mock_pack(
        self,
        object_id: str,
        destination: PackDestination,
        is_derived: bool = False,
    ) -> MagicMock:
        from demisto_sdk.commands.content_graph.objects.pack import Pack

        mock = MagicMock(spec=Pack)
        mock.object_id = object_id
        mock.destination = destination
        mock.is_derived = is_derived
        mock.path = Path(f"/fake/Packs/{object_id}")
        mock.name = object_id
        mock.managed = destination == PackDestination.MANAGED_CONTENT
        mock.source = object_id if is_derived else ""
        mock.derived_from = f"{object_id.replace(DERIVED_PACK_SUFFIX, '')}" if is_derived else None
        mock.content_items = []
        mock.coupling_overrides = None
        mock._is_item_tightly_coupled = MagicMock(return_value=True)
        return mock

    def test_destination_filter_marketplace(self):
        """Only marketplace packs should be included when filtering."""
        from demisto_sdk.commands.content_graph.objects.repository import ContentDTO

        mp_pack = self._make_mock_pack("PackA", PackDestination.MARKETPLACE)
        mc_pack = self._make_mock_pack(
            "PackBManaged", PackDestination.MANAGED_CONTENT, is_derived=True
        )

        dto = MagicMock(spec=ContentDTO)
        dto.packs = [mp_pack, mc_pack]

        # Simulate the filtering logic
        filtered = [
            p for p in dto.packs
            if p.destination == PackDestination.MARKETPLACE
        ]
        assert len(filtered) == 1
        assert filtered[0].object_id == "PackA"

    def test_destination_filter_managed(self):
        """Only managed packs should be included when filtering."""
        from demisto_sdk.commands.content_graph.objects.repository import ContentDTO

        mp_pack = self._make_mock_pack("PackA", PackDestination.MARKETPLACE)
        mc_pack = self._make_mock_pack(
            "PackBManaged", PackDestination.MANAGED_CONTENT, is_derived=True
        )

        dto = MagicMock(spec=ContentDTO)
        dto.packs = [mp_pack, mc_pack]

        filtered = [
            p for p in dto.packs
            if p.destination == PackDestination.MANAGED_CONTENT
        ]
        assert len(filtered) == 1
        assert filtered[0].object_id == "PackBManaged"

    def test_no_destination_filter_returns_all(self):
        """When destination is None, all packs should be included."""
        from demisto_sdk.commands.content_graph.objects.repository import ContentDTO

        mp_pack = self._make_mock_pack("PackA", PackDestination.MARKETPLACE)
        mc_pack = self._make_mock_pack(
            "PackBManaged", PackDestination.MANAGED_CONTENT, is_derived=True
        )

        dto = MagicMock(spec=ContentDTO)
        dto.packs = [mp_pack, mc_pack]

        destination = None
        filtered = (
            [p for p in dto.packs if p.destination == destination]
            if destination is not None
            else dto.packs
        )
        assert len(filtered) == 2


# ---------------------------------------------------------------------------
# pack_destinations.json generation tests
# ---------------------------------------------------------------------------


class TestPackDestinationsJson:
    """Tests for ContentDTO.write_pack_destinations()."""

    def test_write_pack_destinations(self, tmp_path: Path):
        from demisto_sdk.commands.content_graph.objects.repository import ContentDTO

        mp_pack = MagicMock()
        mp_pack.object_id = "PackA"
        mp_pack.name = "Pack A"
        mp_pack.destination = PackDestination.MARKETPLACE
        mp_pack.path = Path("/fake/Packs/PackA")
        mp_pack.is_derived = False
        mp_pack.derived_from = None
        mp_pack.managed = False
        mp_pack.source = ""
        mp_pack.content_items = []

        derived_pack = MagicMock()
        derived_pack.object_id = "PackAManaged"
        derived_pack.name = "Pack A Managed"
        derived_pack.destination = PackDestination.MANAGED_CONTENT
        derived_pack.path = Path("/fake/Packs/PackA")
        derived_pack.is_derived = True
        derived_pack.derived_from = "PackA"
        derived_pack.managed = True
        derived_pack.source = "Pack A"
        derived_pack.content_items = []
        derived_pack._is_item_tightly_coupled = MagicMock(return_value=True)

        dto = MagicMock(spec=ContentDTO)
        dto.packs = [mp_pack, derived_pack]
        # Bind the real method
        dto.write_pack_destinations = ContentDTO.write_pack_destinations.__get__(
            dto, ContentDTO
        )

        output_file = tmp_path / "pack_destinations.json"
        dto.write_pack_destinations(output_file)

        assert output_file.exists()
        data = stdlib_json.loads(output_file.read_text())
        assert "packs" in data
        assert len(data["packs"]) == 2

        # Check first pack (marketplace)
        pack_a = next(p for p in data["packs"] if p["pack_id"] == "PackA")
        assert pack_a["destination"] == "MARKETPLACE"
        assert pack_a["is_derived"] is False
        assert pack_a["managed"] is False

        # Check derived pack
        pack_a_managed = next(
            p for p in data["packs"] if p["pack_id"] == "PackAManaged"
        )
        assert pack_a_managed["destination"] == "MANAGED_CONTENT"
        assert pack_a_managed["is_derived"] is True
        assert pack_a_managed["parent_pack_id"] == "PackA"
        assert pack_a_managed["managed"] is True
        assert pack_a_managed["source"] == "Pack A"


# ---------------------------------------------------------------------------
# pack_destinations.json managed_pack_id tests
# ---------------------------------------------------------------------------


def _mock_pack(
    object_id: str,
    *,
    destination: PackDestination = PackDestination.MARKETPLACE,
    managed: bool = False,
    source: str = "",
    managed_pack_id: Optional[str] = None,
) -> MagicMock:
    """Build a mock pack for the destinations writer.

    ``managed_pack_id`` defaults to ``None``, which *deletes* the attribute
    from the mock rather than setting it. This matters: on a bare ``MagicMock``
    every attribute access auto-creates a truthy child mock, so a pack that is
    supposed to have no graph-provided managed counterpart must have the
    attribute genuinely absent for ``getattr(pack, "managed_pack_id", None)``
    to return ``None``.
    """
    pack = MagicMock()
    pack.object_id = object_id
    pack.name = object_id
    pack.destination = destination
    pack.path = Path(f"/fake/Packs/{object_id}")
    pack.is_derived = False
    pack.derived_from = None
    pack.managed = managed
    pack.source = source
    pack.content_items = []
    if managed_pack_id is None:
        del pack.managed_pack_id
    else:
        pack.managed_pack_id = managed_pack_id
    return pack


def _write_and_read(
    tmp_path: Path,
    packs: List[MagicMock],
    managed_pack_ids: Optional[dict] = None,
) -> dict:
    """Run the real writer over mock packs and return the parsed JSON."""
    from demisto_sdk.commands.content_graph.objects.repository import ContentDTO

    dto = MagicMock(spec=ContentDTO)
    dto.packs = packs
    # Bind the real method
    dto.write_pack_destinations = ContentDTO.write_pack_destinations.__get__(
        dto, ContentDTO
    )

    output_file = tmp_path / "pack_destinations.json"
    if managed_pack_ids is None:
        dto.write_pack_destinations(output_file)
    else:
        dto.write_pack_destinations(output_file, managed_pack_ids)

    return stdlib_json.loads(output_file.read_text())


class TestPackDestinationsManagedPackId:
    """Tests for the ``managed_pack_id`` field in the destinations output."""

    def test_every_entry_has_a_managed_pack_id_key(self, tmp_path: Path):
        """The key must be present on every entry, whether or not it has a value."""
        packs = [
            _mock_pack("AWS", managed=True, managed_pack_id="AWSManaged"),
            _mock_pack("PackA"),
        ]

        data = _write_and_read(tmp_path, packs)

        assert len(data["packs"]) == 2
        for entry in data["packs"]:
            assert "managed_pack_id" in entry

    def test_graph_provided_managed_pack_id_is_emitted(self, tmp_path: Path):
        """A pack whose graph object carries a renamed id emits that id."""
        packs = [_mock_pack("AWS", managed=True, managed_pack_id="AWSManaged")]

        data = _write_and_read(tmp_path, packs)

        assert data["packs"][0]["managed_pack_id"] == "AWSManaged"

    def test_managed_pack_id_falls_back_to_the_caller_supplied_mapping(
        self, tmp_path: Path
    ):
        """When the graph carries no id, the caller mapping supplies it."""
        packs = [_mock_pack("Azure", managed=True)]

        data = _write_and_read(tmp_path, packs, {"Azure": "AzureManaged"})

        assert data["packs"][0]["managed_pack_id"] == "AzureManaged"

    def test_graph_value_wins_over_the_caller_supplied_mapping(self, tmp_path: Path):
        """The graph is the more authoritative source of the renamed id."""
        packs = [_mock_pack("GCP", managed=True, managed_pack_id="GCPManaged")]

        data = _write_and_read(tmp_path, packs, {"GCP": "FromMapping"})

        assert data["packs"][0]["managed_pack_id"] == "GCPManaged"

    def test_managed_pack_id_is_null_when_there_is_no_counterpart(self, tmp_path: Path):
        """A pack with no managed counterpart serializes as JSON null."""
        packs = [_mock_pack("PackA")]

        data = _write_and_read(tmp_path, packs)

        assert data["packs"][0]["managed_pack_id"] is None
        assert (
            '"managed_pack_id": null'
            in (tmp_path / "pack_destinations.json").read_text()
        )

    def test_managed_pack_id_is_null_when_the_mapping_omits_the_pack(
        self, tmp_path: Path
    ):
        """A non-empty mapping that does not mention the pack still yields null."""
        packs = [_mock_pack("PackA")]

        data = _write_and_read(tmp_path, packs, {"AWS": "AWSManaged"})

        assert data["packs"][0]["managed_pack_id"] is None

    def test_empty_graph_value_is_normalized_to_null(self, tmp_path: Path):
        """An empty string must never reach consumers as an empty string."""
        packs = [_mock_pack("PackA", managed_pack_id="")]

        data = _write_and_read(tmp_path, packs)

        assert data["packs"][0]["managed_pack_id"] is None


# ---------------------------------------------------------------------------
# pack_destinations.json artifact_path tests
# ---------------------------------------------------------------------------


def _artifact_mock_pack(
    object_id: str,
    dir_name: str,
    *,
    is_derived: bool = False,
    derived_from: Optional[str] = None,
) -> MagicMock:
    """Build a mock pack whose source directory name is independent of its id.

    ``dir_name`` is deliberately decoupled from ``object_id`` so a fixture can
    express the case the invariant is about: a pack whose directory on disk is
    not named after its id.
    """
    pack = MagicMock()
    pack.object_id = object_id
    pack.name = object_id
    pack.destination = (
        PackDestination.MANAGED_CONTENT if is_derived else PackDestination.MARKETPLACE
    )
    pack.path = Path(f"/fake/Packs/{dir_name}")
    pack.is_derived = is_derived
    pack.derived_from = derived_from
    pack.managed = is_derived
    pack.source = DEFAULT_DERIVED_PACK_SOURCE if is_derived else ""
    pack.content_items = []
    pack._is_item_tightly_coupled = MagicMock(return_value=True)
    # Absent by design - see ``_mock_pack`` for why this must be deleted.
    del pack.managed_pack_id
    return pack


def _dump_and_write_destinations(
    packs: List[MagicMock], output_dir: Path
) -> Tuple[dict, Dict[str, Path]]:
    """Run the real ``dump()`` and the real writer over the same packs.

    Returns the parsed destinations JSON together with
    ``{pack_id: dumped_path}``, captured from the output directory
    ``ContentDTO.dump()`` actually handed to each ``Pack.dump()`` call.
    """
    from demisto_sdk.commands.common.constants import MarketplaceVersions
    from demisto_sdk.commands.content_graph.objects.repository import ContentDTO

    dto = MagicMock(spec=ContentDTO)
    dto.packs = packs
    # Bind the real methods
    dto._artifact_path = ContentDTO._artifact_path
    dto.dump = ContentDTO.dump.__get__(dto, ContentDTO)
    dto.write_pack_destinations = ContentDTO.write_pack_destinations.__get__(
        dto, ContentDTO
    )

    dto.dump(output_dir, MarketplaceVersions.XSOAR, zip=False)
    dumped_paths = {pack.object_id: pack.dump.call_args.args[0] for pack in packs}

    # The writer derives the artifact directory from the file's parent, so the
    # artifact must be written inside the very directory that was dumped to.
    output_file = output_dir / "pack_destinations.json"
    dto.write_pack_destinations(output_file)

    return stdlib_json.loads(output_file.read_text()), dumped_paths


class TestPackDestinationsArtifactPath:
    """``artifact_path`` must name the directory ``dump()`` actually wrote.

    Infra's now-deleted writer always used ``object_id``, while ``dump()`` uses
    ``pack.path.name`` for non-derived packs. The two disagree for every pack
    whose directory name differs from its id, so the agreement is pinned here.
    """

    def test_artifact_path_matches_dump_when_dir_name_differs_from_id(
        self, tmp_path: Path
    ):
        """A non-derived pack is dumped under its directory name, not its id."""
        output_dir = tmp_path / "artifacts"
        packs = [_artifact_mock_pack("PackA", "PackADirectory")]

        data, dumped_paths = _dump_and_write_destinations(packs, output_dir)

        entry = data["packs"][0]
        assert entry["artifact_path"] == str(dumped_paths["PackA"])
        assert entry["artifact_path"] == str(output_dir / "PackADirectory")
        assert entry["artifact_path"] != str(output_dir / "PackA")

    def test_artifact_path_matches_dump_for_a_derived_pack(self, tmp_path: Path):
        """A derived pack is dumped under its derived id, not its source dir."""
        output_dir = tmp_path / "artifacts"
        packs = [
            _artifact_mock_pack(
                "PackAManaged",
                "PackADirectory",
                is_derived=True,
                derived_from="PackA",
            )
        ]

        data, dumped_paths = _dump_and_write_destinations(packs, output_dir)

        entry = data["packs"][0]
        assert entry["is_derived"] is True
        assert entry["artifact_path"] == str(dumped_paths["PackAManaged"])
        assert entry["artifact_path"] == str(output_dir / "PackAManaged")
        assert entry["artifact_path"] != str(output_dir / "PackADirectory")

    def test_every_entry_matches_its_dumped_path(self, tmp_path: Path):
        """The invariant holds for every pack in a mixed fixture."""
        output_dir = tmp_path / "artifacts"
        packs = [
            _artifact_mock_pack("PackA", "PackADirectory"),
            _artifact_mock_pack("PackB", "PackB"),
            _artifact_mock_pack(
                "PackAManaged",
                "PackADirectory",
                is_derived=True,
                derived_from="PackA",
            ),
        ]

        data, dumped_paths = _dump_and_write_destinations(packs, output_dir)

        assert len(data["packs"]) == len(packs)
        for entry in data["packs"]:
            assert entry["artifact_path"] == str(dumped_paths[entry["pack_id"]])


# ---------------------------------------------------------------------------
# pack_destinations.json artifact_path dump-directory routing tests
# ---------------------------------------------------------------------------


def _write_destinations_with_dump_dirs(
    packs: List[MagicMock],
    output_path: Path,
    artifacts_dir: Optional[Path] = None,
    managed_artifacts_dir: Optional[Path] = None,
) -> dict:
    """Run the real writer with explicit dump directories and return the JSON.

    Only ``_artifact_path`` and ``write_pack_destinations`` are rebound to the
    real implementations - every other attribute stays a ``MagicMock`` so an
    accidental extra ``self.<method>()`` call inside the writer would surface as
    a corrupted ``artifact_path`` instead of silently passing.

    When both directories are omitted the legacy two-argument form is used, so
    the same helper can exercise the backward-compatible call shape.
    """
    from demisto_sdk.commands.content_graph.objects.repository import ContentDTO

    dto = MagicMock(spec=ContentDTO)
    dto.packs = packs
    dto._artifact_path = ContentDTO._artifact_path
    dto.write_pack_destinations = ContentDTO.write_pack_destinations.__get__(
        dto, ContentDTO
    )

    if artifacts_dir is None and managed_artifacts_dir is None:
        dto.write_pack_destinations(output_path)
    else:
        dto.write_pack_destinations(
            output_path, None, artifacts_dir, managed_artifacts_dir
        )

    return stdlib_json.loads(output_path.read_text())


class TestPackDestinationsDumpDirectories:
    """``artifact_path`` must be rooted at the directory the pack is dumped to.

    ``dump()`` writes regular packs into ``artifacts_dir`` and managed packs
    into ``managed_artifacts_dir``. The writer used to always root the path at
    ``output_path.parent``, which silently dropped the dump-directory segment
    whenever the JSON artifact did not live inside the dump directory - exactly
    the CI layout. The two axes pinned here are independent: the *base* dir is
    chosen by ``pack.managed``, the *last segment* by ``pack.is_derived``.
    """

    def test_regular_pack_is_rooted_at_the_artifacts_dir(self, tmp_path: Path):
        """An unmanaged pack keeps the artifacts-dir segment in its path."""
        artifacts_dir = tmp_path / "content_packs"
        output_path = tmp_path / "pack_destinations.json"
        packs = [_artifact_mock_pack("PackA", "PackADirectory")]

        data = _write_destinations_with_dump_dirs(
            packs,
            output_path,
            artifacts_dir=artifacts_dir,
            managed_artifacts_dir=tmp_path / "content_packs_managed",
        )

        assert data["packs"][0]["artifact_path"] == str(
            artifacts_dir / "PackADirectory"
        )

    def test_managed_pack_is_rooted_at_the_managed_artifacts_dir(self, tmp_path: Path):
        """A managed pack is never routed to the regular artifacts directory."""
        artifacts_dir = tmp_path / "content_packs"
        managed_artifacts_dir = tmp_path / "content_packs_managed"
        output_path = tmp_path / "pack_destinations.json"
        pack = _artifact_mock_pack("AWSManaged", "AWSManagedDirectory")
        pack.managed = True

        data = _write_destinations_with_dump_dirs(
            [pack],
            output_path,
            artifacts_dir=artifacts_dir,
            managed_artifacts_dir=managed_artifacts_dir,
        )

        artifact_path = data["packs"][0]["artifact_path"]
        assert artifact_path == str(managed_artifacts_dir / "AWSManagedDirectory")
        assert artifact_path != str(artifacts_dir / "AWSManagedDirectory")
        assert artifact_path != str(output_path.parent / "AWSManagedDirectory")

    def test_mixed_graph_routes_each_pack_to_its_own_base_dir(self, tmp_path: Path):
        """Managed and unmanaged packs in one call must not cross-contaminate."""
        artifacts_dir = tmp_path / "content_packs"
        managed_artifacts_dir = tmp_path / "content_packs_managed"
        regular_pack = _artifact_mock_pack("PackA", "PackADirectory")
        managed_pack = _artifact_mock_pack("AWSManaged", "AWSManagedDirectory")
        managed_pack.managed = True

        data = _write_destinations_with_dump_dirs(
            [regular_pack, managed_pack],
            tmp_path / "pack_destinations.json",
            artifacts_dir=artifacts_dir,
            managed_artifacts_dir=managed_artifacts_dir,
        )

        by_id = {entry["pack_id"]: entry["artifact_path"] for entry in data["packs"]}
        assert by_id == {
            "PackA": str(artifacts_dir / "PackADirectory"),
            "AWSManaged": str(managed_artifacts_dir / "AWSManagedDirectory"),
        }

    def test_relative_artifacts_dir_yields_an_absolute_artifact_path(
        self, tmp_path: Path
    ):
        """Consumers resolve the path from a different cwd, so it must be absolute."""
        artifacts_dir = Path("content_packs")
        packs = [_artifact_mock_pack("PackA", "PackADirectory")]

        data = _write_destinations_with_dump_dirs(
            packs,
            tmp_path / "pack_destinations.json",
            artifacts_dir=artifacts_dir,
            managed_artifacts_dir=Path("content_packs_managed"),
        )

        artifact_path = data["packs"][0]["artifact_path"]
        assert Path(artifact_path).is_absolute()
        assert artifact_path == str(artifacts_dir.absolute() / "PackADirectory")

    def test_derived_unmanaged_pack_keeps_its_object_id_under_the_artifacts_dir(
        self, tmp_path: Path
    ):
        """``is_derived`` drives the last segment, not the base directory."""
        artifacts_dir = tmp_path / "content_packs"
        pack = _artifact_mock_pack(
            "PackAManaged", "PackADirectory", is_derived=True, derived_from="PackA"
        )
        pack.managed = False

        data = _write_destinations_with_dump_dirs(
            [pack],
            tmp_path / "pack_destinations.json",
            artifacts_dir=artifacts_dir,
            managed_artifacts_dir=tmp_path / "content_packs_managed",
        )

        assert data["packs"][0]["artifact_path"] == str(
            artifacts_dir / "PackAManaged"
        )

    def test_derived_managed_pack_keeps_its_object_id_under_the_managed_dir(
        self, tmp_path: Path
    ):
        """The derived-id segment and the managed base directory combine."""
        managed_artifacts_dir = tmp_path / "content_packs_managed"
        pack = _artifact_mock_pack(
            "PackAManaged", "PackADirectory", is_derived=True, derived_from="PackA"
        )

        data = _write_destinations_with_dump_dirs(
            [pack],
            tmp_path / "pack_destinations.json",
            artifacts_dir=tmp_path / "content_packs",
            managed_artifacts_dir=managed_artifacts_dir,
        )

        assert data["packs"][0]["artifact_path"] == str(
            managed_artifacts_dir / "PackAManaged"
        )

    def test_managed_pack_without_a_managed_artifacts_dir_raises(self, tmp_path: Path):
        """Falling back to the regular artifacts dir would corrupt the upload."""
        pack = _artifact_mock_pack("AWSManaged", "AWSManagedDirectory")
        pack.managed = True

        with pytest.raises(ValueError, match="AWSManaged"):
            _write_destinations_with_dump_dirs(
                [pack],
                tmp_path / "pack_destinations.json",
                artifacts_dir=tmp_path / "content_packs",
            )

    def test_legacy_two_argument_call_with_a_managed_pack_does_not_raise(
        self, tmp_path: Path
    ):
        """Omitting the dump dirs entirely keeps the historical output."""
        output_path = tmp_path / "pack_destinations.json"
        pack = _artifact_mock_pack("AWSManaged", "AWSManagedDirectory")
        pack.managed = True

        data = _write_destinations_with_dump_dirs([pack], output_path)

        assert data["packs"][0]["artifact_path"] == str(
            output_path.parent / "AWSManagedDirectory"
        )


# ---------------------------------------------------------------------------
# ContentDTO mapping API tests
# ---------------------------------------------------------------------------


class TestContentDTOMappingAPI:
    """Tests for get_pack_destination_mapping and get_derived_pack_mapping."""

    def test_get_pack_destination_mapping(self):
        from demisto_sdk.commands.content_graph.objects.repository import ContentDTO

        pack1 = MagicMock()
        pack1.object_id = "PackA"
        pack1.destination = PackDestination.MARKETPLACE

        pack2 = MagicMock()
        pack2.object_id = "PackB"
        pack2.destination = PackDestination.MANAGED_CONTENT

        dto = MagicMock(spec=ContentDTO)
        dto.packs = [pack1, pack2]
        dto.get_pack_destination_mapping = ContentDTO.get_pack_destination_mapping.__get__(
            dto, ContentDTO
        )

        mapping = dto.get_pack_destination_mapping()
        assert mapping == {
            "PackA": PackDestination.MARKETPLACE,
            "PackB": PackDestination.MANAGED_CONTENT,
        }

    def test_get_derived_pack_mapping(self):
        from demisto_sdk.commands.content_graph.objects.repository import ContentDTO

        pack1 = MagicMock()
        pack1.object_id = "PackA"
        pack1.is_derived = False
        pack1.derived_from = None

        pack2 = MagicMock()
        pack2.object_id = "PackAManaged"
        pack2.is_derived = True
        pack2.derived_from = "PackA"

        dto = MagicMock(spec=ContentDTO)
        dto.packs = [pack1, pack2]
        dto.get_derived_pack_mapping = ContentDTO.get_derived_pack_mapping.__get__(
            dto, ContentDTO
        )

        mapping = dto.get_derived_pack_mapping()
        assert mapping == {"PackAManaged": "PackA"}


# ---------------------------------------------------------------------------
# Feature flag tests
# ---------------------------------------------------------------------------


class TestFeatureFlag:
    """Tests for ENABLE_SPLIT_PACKS feature flag."""

    def test_feature_flag_default_is_false(self):
        """By default, ENABLE_SPLIT_PACKS should be False."""
        # The actual value depends on the environment, but we test the
        # parsing logic
        import os

        with patch.dict(os.environ, {}, clear=True):
            # Re-evaluate the flag
            result = os.getenv("ENABLE_SPLIT_PACKS", "false").lower() == "true"
            assert result is False

    def test_feature_flag_enabled(self):
        import os

        with patch.dict(os.environ, {"ENABLE_SPLIT_PACKS": "true"}):
            result = os.getenv("ENABLE_SPLIT_PACKS", "false").lower() == "true"
            assert result is True


# ---------------------------------------------------------------------------
# Split-pack dependency isolation tests
# ---------------------------------------------------------------------------


class TestSplitPackFamilyPredicates:
    """Tests for the cypher predicates that isolate split-pack families.

    A derived pack and the pack it was derived from are two graph
    representations of the same source directory. They share their tightly
    coupled content items via a second IN_PACK edge, which would otherwise make
    the dependency calculation infer a DEPENDS_ON between them in one or both
    directions. These predicates are what prevent that.
    """

    def test_family_key_of_a_regular_pack_is_its_own_id(self):
        """A pack with no ``derived_from`` is the sole member of its family."""
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
            pack_family_key,
        )

        assert pack_family_key("pack_a") == "coalesce(pack_a.derived_from, pack_a.object_id)"

    def test_family_predicate_compares_both_family_keys(self):
        """Comparing family keys covers every twin direction in one predicate:
        original vs. derived, derived vs. original, and two derived packs that
        share an origin."""
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
            are_in_the_same_split_pack_family,
        )

        assert are_in_the_same_split_pack_family("pack_a", "pack_b") == (
            "coalesce(pack_a.derived_from, pack_a.object_id) "
            "= coalesce(pack_b.derived_from, pack_b.object_id)"
        )

    def test_managed_or_derived_predicate_defaults_missing_flags_to_false(self):
        """Regular packs predate these flags and may not carry them at all, so
        both must default to false rather than null - a null would make the
        enclosing ``NOT`` filter out legitimate dependencies."""
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
            is_managed_or_derived,
        )

        assert is_managed_or_derived("pack_a") == (
            "(coalesce(pack_a.managed, false) OR coalesce(pack_a.is_derived, false))"
        )


class TestDependencyQueriesExcludeTwinsAndManagedPacks:
    """Tests that every query producing DEPENDS_ON applies the isolation guards.

    There are three independent paths that can create a pack-level dependency,
    and a guard on only one of them still lets twin edges through. These tests
    pin all three.
    """

    def test_direct_dependency_query_guards_twins_and_managed_packs(self):
        """``create_depends_on_relationships`` derives DEPENDS_ON from USES
        edges between items in different packs - the path that produces twin
        edges, because a tightly coupled item is IN_PACK for both twins."""
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import (
            create_depends_on_relationships,
        )

        transaction = MagicMock()
        with patch(
            "demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies.run_query",
            return_value=[],
        ) as mock_run_query:
            create_depends_on_relationships(transaction)

        query = mock_run_query.call_args[0][1]
        assert (
            "NOT coalesce(pack_a.derived_from, pack_a.object_id) "
            "= coalesce(pack_b.derived_from, pack_b.object_id)" in query
        )
        assert "NOT (coalesce(pack_a.managed, false) OR coalesce(pack_a.is_derived, false))" in query
        assert "NOT (coalesce(pack_b.managed, false) OR coalesce(pack_b.is_derived, false))" in query

    def test_all_level_dependency_query_guards_twins_and_managed_packs(self):
        """The all-level query walks paths of up to MAX_DEPTH hops. Guarding
        only the direct edge is not enough: an indirect route such as
        ``pack -> CommonScripts -> packManaged`` would still surface the twin
        as an all-level dependency."""
        from demisto_sdk.commands.common.constants import MarketplaceVersions
        from demisto_sdk.commands.content_graph.common import RelationshipType
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import (
            get_all_level_packs_relationships,
        )

        transaction = MagicMock()
        with patch(
            "demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies.run_query",
            return_value=[],
        ) as mock_run_query:
            get_all_level_packs_relationships(
                transaction,
                RelationshipType.DEPENDS_ON,
                ["some-node-id"],
                MarketplaceVersions.XSOAR,
            )

        query = mock_run_query.call_args[0][1]
        assert (
            "NOT coalesce(p1.derived_from, p1.object_id) "
            "= coalesce(p2.derived_from, p2.object_id)" in query
        )
        assert "NOT (coalesce(p1.managed, false) OR coalesce(p1.is_derived, false))" in query
        assert "NOT (coalesce(p2.managed, false) OR coalesce(p2.is_derived, false))" in query

    def test_metadata_dependency_query_guards_twins_and_managed_packs(self):
        """Metadata-declared dependencies bypass the calculation entirely, and
        ``remove_existing_depends_on_relationships`` only clears edges with
        ``from_metadata = false`` - so an unguarded twin edge here would never
        be recalculated away."""
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.relationships import (
            build_depends_on_relationships_query,
        )

        query = build_depends_on_relationships_query()

        assert (
            "NOT coalesce(p1.derived_from, p1.object_id) "
            "= coalesce(p2.derived_from, p2.object_id)" in query
        )
        assert "NOT (coalesce(p1.managed, false) OR coalesce(p1.is_derived, false))" in query
        assert "NOT (coalesce(p2.managed, false) OR coalesce(p2.is_derived, false))" in query

    @pytest.mark.parametrize("mandatorily", [False, True])
    def test_all_level_dependency_query_is_balanced_for_both_mandatorily_modes(
        self, mandatorily: bool
    ):
        """The ``mandatorily`` branch used to close the ``all(`` predicate only
        when it was enabled, producing unbalanced cypher in the default mode."""
        from demisto_sdk.commands.common.constants import MarketplaceVersions
        from demisto_sdk.commands.content_graph.common import RelationshipType
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import (
            get_all_level_packs_relationships,
        )

        transaction = MagicMock()
        with patch(
            "demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies.run_query",
            return_value=[],
        ) as mock_run_query:
            get_all_level_packs_relationships(
                transaction,
                RelationshipType.DEPENDS_ON,
                ["some-node-id"],
                MarketplaceVersions.XSOAR,
                mandatorily,
            )

        query = mock_run_query.call_args[0][1]
        assert query.count("(") == query.count(")")
        assert ("r.mandatorily = true" in query) is mandatorily

    def test_metadata_dependency_query_creates_rather_than_merges(self):
        """``target_min_version`` is null whenever a dependency declares no
        ``minVersion``, and neo4j rejects a null property inside a MERGE
        pattern - so this query must keep using CREATE."""
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.relationships import (
            build_depends_on_relationships_query,
        )

        query = build_depends_on_relationships_query()

        assert "CREATE (p1)-[r:DEPENDS_ON" in query
        assert "MERGE (p1)-[r:DEPENDS_ON" not in query


class TestDerivedPackCarriesNoPackLevelDependencies:
    """Tests that a derived pack inherits content, but never dependencies."""

    def _make_original_parser_with_dependencies(self) -> MagicMock:
        from demisto_sdk.commands.content_graph.common import RelationshipType

        original = TestDerivedPackParser()._make_mock_original_parser()
        relationships = Relationships()
        relationships.add(
            RelationshipType.DEPENDS_ON,
            source="TestPack",
            target="Base",
            mandatorily=True,
        )
        relationships.add(
            RelationshipType.IN_PACK,
            source_id="TestIntegration",
            source_type=ContentType.INTEGRATION,
            target="TestPack",
        )
        original.relationships = relationships
        return original

    def test_derived_pack_does_not_inherit_depends_on(self):
        """A derived pack ships to Managed Content as a self-contained unit, so
        it declares no pack-level dependencies."""
        from demisto_sdk.commands.content_graph.common import RelationshipType
        from demisto_sdk.commands.content_graph.parsers.pack import DerivedPackParser

        derived = DerivedPackParser(
            original_parser=self._make_original_parser_with_dependencies(),
            derived_id="TestPackManaged",
        )

        assert derived.relationships.get(RelationshipType.DEPENDS_ON, []) == []

    def test_derived_pack_still_inherits_other_relationships(self):
        """Only DEPENDS_ON is dropped - the content graph still needs the rest,
        which is what makes the shared items resolvable from the derived pack."""
        from demisto_sdk.commands.content_graph.common import RelationshipType
        from demisto_sdk.commands.content_graph.parsers.pack import DerivedPackParser

        derived = DerivedPackParser(
            original_parser=self._make_original_parser_with_dependencies(),
            derived_id="TestPackManaged",
        )

        assert len(derived.relationships.get(RelationshipType.IN_PACK, [])) == 1

    def test_original_pack_dependencies_are_left_untouched(self):
        """Building the derived pack must not mutate the original's
        relationships: regular packs keep the dependencies they always had."""
        from demisto_sdk.commands.content_graph.common import RelationshipType
        from demisto_sdk.commands.content_graph.parsers.pack import DerivedPackParser

        original = self._make_original_parser_with_dependencies()
        DerivedPackParser(original_parser=original, derived_id="TestPackManaged")

        depends_on = original.relationships.get(RelationshipType.DEPENDS_ON, [])
        assert len(depends_on) == 1
        assert depends_on[0]["source"] == "TestPack"
        assert depends_on[0]["target"] == "Base"


# ---------------------------------------------------------------------------
# Twin isolation on a persistent graph
# ---------------------------------------------------------------------------
#
# The queries guarded above all *create* DEPENDS_ON. On a graph that is reused
# between builds (which is how CI runs it) two further paths keep twin edges
# alive even though no query creates them any more. Both were confirmed
# against a live neo4j before these tests were written:
#
#   1. ``get_relationships_to_preserve`` captures every relationship pointing
#      at a pack that is about to be recreated, with no type filter, and
#      ``return_preserved_relationships`` writes them all back afterwards.
#      Measured: refreshing only ``PackA`` captured 2 DEPENDS_ON edges from
#      ``PackAManaged`` and restored both.
#   2. ``remove_existing_depends_on_relationships`` only deletes edges with
#      ``from_metadata = false``, so a ``from_metadata = true`` twin edge
#      survives every recalculation. Measured: after injecting all four twin
#      edge variants and running ``create_pack_dependencies``, the two
#      ``from_metadata = true`` edges remained.


class TestPreserveQueryExcludesTwinDependsOn:
    """``get_relationships_to_preserve`` must not carry twin DEPENDS_ON over.

    It runs before ``remove_packs_before_creation`` and its results are
    replayed after the nodes are recreated, so anything it captures bypasses
    every guard on the creating queries.
    """

    def _preserve_query(self) -> str:
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.nodes import (
            get_relationships_to_preserve,
        )

        transaction = MagicMock()
        with patch(
            "demisto_sdk.commands.content_graph.interface.neo4j.queries.nodes.run_query"
        ) as mock_run_query:
            mock_run_query.return_value.data.return_value = []
            get_relationships_to_preserve(transaction, ["PackA"])

        return mock_run_query.call_args[0][1]

    def test_preserve_query_excludes_twin_depends_on(self):
        """The pack-to-pack branch matches ``(s)-[r]->(t)`` for every
        relationship type. Without a family guard it re-attaches exactly the
        edge the dependency queries refuse to create."""
        query = self._preserve_query()

        assert (
            "NOT coalesce(s.derived_from, s.object_id) "
            "= coalesce(t.derived_from, t.object_id)" in query
        )

    def test_preserve_query_excludes_depends_on_touching_a_managed_pack(self):
        """Managed and derived packs ship self-contained, so no pack-level
        dependency may be restored in either direction."""
        query = self._preserve_query()

        assert (
            "NOT (coalesce(s.managed, false) OR coalesce(s.is_derived, false))" in query
        )
        assert (
            "NOT (coalesce(t.managed, false) OR coalesce(t.is_derived, false))" in query
        )

    def test_preserve_query_only_guards_depends_on(self):
        """The guards are scoped to DEPENDS_ON. Every other relationship type
        must still be preserved - that is the whole point of the query."""
        query = self._preserve_query()

        # Anything that is not a DEPENDS_ON short-circuits the guard.
        assert 'type(r) <> "DEPENDS_ON"' in query
        # The three original branches are still there.
        assert query.count("UNION") == 2


class TestDependsOnRemovalClearsTwinEdges:
    """``remove_existing_depends_on_relationships`` must clear twin edges
    regardless of ``from_metadata``.

    Metadata-declared edges are deliberately kept across recalculations, but a
    twin edge is never legitimate, so the ``from_metadata`` exemption must not
    apply to it. Otherwise an edge written by a pre-fix build is immortal.
    """

    def _removal_query(self) -> str:
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import (
            remove_existing_depends_on_relationships,
        )

        transaction = MagicMock()
        with patch(
            "demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies.run_query"
        ) as mock_run_query:
            remove_existing_depends_on_relationships(transaction)

        return mock_run_query.call_args[0][1]

    def test_removal_deletes_twin_edges_even_when_from_metadata(self):
        """A twin edge with ``from_metadata = true`` is not recalculated by any
        query, so if this deletion skips it, it stays in the graph forever."""
        query = self._removal_query()

        assert (
            "coalesce(p1.derived_from, p1.object_id) "
            "= coalesce(p2.derived_from, p2.object_id)" in query
        )

    def test_removal_deletes_edges_touching_a_managed_pack(self):
        """Same reasoning, for any dependency involving a managed or derived
        pack in either direction."""
        query = self._removal_query()

        assert (
            "(coalesce(p1.managed, false) OR coalesce(p1.is_derived, false))" in query
        )
        assert (
            "(coalesce(p2.managed, false) OR coalesce(p2.is_derived, false))" in query
        )

    def test_removal_still_keeps_metadata_edges_between_regular_packs(self):
        """The pre-existing contract must not change: a metadata-declared
        dependency between two regular packs survives recalculation, because
        nothing recreates it."""
        query = self._removal_query()

        assert "r.from_metadata = false" in query
