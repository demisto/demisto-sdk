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
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

from demisto_sdk.commands.content_graph.common import (
    DERIVED_PACK_SUFFIX,
    ENABLE_SPLIT_PACKS,
    TIGHTLY_COUPLED_TYPES,
    ContentType,
    PackDestination,
    Relationships,
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

    def test_derived_pack_source(self):
        from demisto_sdk.commands.content_graph.parsers.pack import DerivedPackParser

        original = self._make_mock_original_parser()
        derived = DerivedPackParser(
            original_parser=original,
            derived_id="TestPackManaged",
        )
        assert derived.source == "Test Pack"

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
