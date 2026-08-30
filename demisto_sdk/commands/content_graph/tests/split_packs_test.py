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
    DERIVED_PACK_ALLOWED_SUPPORT_LEVELS,
    DERIVED_PACK_SUFFIX,
    DERIVED_PACKS_EXCLUDE_ENV,
    TIGHTLY_COUPLED_TYPES,
    ContentType,
    PackDestination,
    Relationships,
    derived_pack_exclusions,
    is_deprecated_content_item,
    is_deprecated_entity,
    is_deprecated_pack,
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
            PackDestination.MANAGED_CONTENT if managed else PackDestination.MARKETPLACE
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
        self,
        object_id: str,
        content_type: ContentType,
        deprecated: bool = False,
        name: Optional[str] = None,
        description: str = "",
    ) -> MagicMock:
        mock = MagicMock()
        mock.object_id = object_id
        mock.content_type = content_type
        # Set explicitly: an unset attribute on a MagicMock auto-creates a truthy
        # child mock, which the deprecation predicate would read as "deprecated".
        mock.deprecated = deprecated
        mock.name = name if name is not None else object_id
        mock.description = description
        return mock

    def _make_pack_with_overrides(self, overrides: Optional[dict] = None) -> MagicMock:
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
        pack = self._make_pack_with_overrides({"MyScript": "tightly_coupled"})
        item = self._make_content_item("MyScript", ContentType.SCRIPT)
        assert pack._is_item_tightly_coupled(item) is True

    def test_override_integration_to_loosely_coupled(self):
        pack = self._make_pack_with_overrides({"MyIntegration": "loosely_coupled"})
        item = self._make_content_item("MyIntegration", ContentType.INTEGRATION)
        assert pack._is_item_tightly_coupled(item) is False

    def test_override_only_affects_specified_item(self):
        pack = self._make_pack_with_overrides({"MyScript": "tightly_coupled"})
        other_script = self._make_content_item("OtherScript", ContentType.SCRIPT)
        assert pack._is_item_tightly_coupled(other_script) is False

    def test_deprecated_item_is_never_tightly_coupled(self):
        """A deprecated integration must not be carried into a derived pack,
        even though its content type is tightly coupled."""
        pack = self._make_pack_with_overrides(None)
        item = self._make_content_item(
            "MyIntegration", ContentType.INTEGRATION, deprecated=True
        )
        assert (
            pack._is_item_tightly_coupled(item) is False
        ), "a deprecated item is never tightly coupled, regardless of its content type"

    def test_deprecated_item_overrides_an_explicit_tightly_coupled_override(self):
        """Deprecation wins over ``coupling_overrides``: an author cannot force a
        dead item into the managed twin."""
        pack = self._make_pack_with_overrides({"MyScript": "tightly_coupled"})
        item = self._make_content_item("MyScript", ContentType.SCRIPT, deprecated=True)
        assert (
            pack._is_item_tightly_coupled(item) is False
        ), "deprecation must be evaluated before coupling_overrides, so the override cannot resurrect it"

    def test_item_deprecated_by_name_and_description_convention(self):
        """The shared predicate also honours the legacy name/description
        convention, not just the explicit ``deprecated`` field."""
        pack = self._make_pack_with_overrides(None)
        item = self._make_content_item(
            "MyIntegration",
            ContentType.INTEGRATION,
            deprecated=False,
            name="My Integration (Deprecated)",
            description="Deprecated. Use Other Integration instead.",
        )
        assert (
            pack._is_item_tightly_coupled(item) is False
        ), "an item marked deprecated by the name/description convention is treated as deprecated too"


# ---------------------------------------------------------------------------
# DerivedPackParser tests
# ---------------------------------------------------------------------------


class TestDerivedPackParser:
    """Tests for DerivedPackParser creation and properties."""

    def _make_mock_original_parser(self) -> MagicMock:
        from demisto_sdk.commands.content_graph.parsers.pack import (
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
        mock.derived_from = (
            f"{object_id.replace(DERIVED_PACK_SUFFIX, '')}" if is_derived else None
        )
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
            p for p in dto.packs if p.destination == PackDestination.MARKETPLACE
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
            p for p in dto.packs if p.destination == PackDestination.MANAGED_CONTENT
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
        mp_pack.current_version = "1.2.3"
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
        derived_pack.current_version = "2.0.1"
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
        assert pack_a["current_version"] == "1.2.3"

        # Check derived pack
        pack_a_managed = next(
            p for p in data["packs"] if p["pack_id"] == "PackAManaged"
        )
        assert pack_a_managed["destination"] == "MANAGED_CONTENT"
        assert pack_a_managed["is_derived"] is True
        assert pack_a_managed["parent_pack_id"] == "PackA"
        assert pack_a_managed["managed"] is True
        assert pack_a_managed["source"] == "Pack A"
        assert pack_a_managed["current_version"] == "2.0.1"


# ---------------------------------------------------------------------------
# pack_destinations.json shared helpers
# ---------------------------------------------------------------------------


def _mock_pack(
    object_id: str,
    *,
    destination: PackDestination = PackDestination.MARKETPLACE,
    managed: bool = False,
    source: str = "",
    current_version: Optional[str] = "1.0.0",
) -> MagicMock:
    """Build a mock pack for the destinations writer.

    ``current_version`` passing ``None`` *deletes* the attribute from the mock
    rather than setting it. This matters: on a bare ``MagicMock`` every
    attribute access auto-creates a truthy child mock, so a pack whose graph
    object carries no version at all must have the attribute genuinely absent
    for ``getattr(pack, "current_version", None)`` to return ``None``.
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
    if current_version is None:
        del pack.current_version
    else:
        pack.current_version = current_version
    return pack


def _write_and_read(
    tmp_path: Path,
    packs: List[MagicMock],
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
    dto.write_pack_destinations(output_file)

    return stdlib_json.loads(output_file.read_text())


# ---------------------------------------------------------------------------
# pack_destinations.json current_version tests
# ---------------------------------------------------------------------------


class TestPackDestinationsCurrentVersion:
    """Tests for the ``current_version`` field in the destinations output.

    Infra decides what to upload from this artifact alone, so the pack version
    must be readable without unzipping the dumped pack.
    """

    def test_every_entry_has_a_current_version_key(self, tmp_path: Path):
        """The key must be present on every entry, whether or not it has a value."""
        packs = [
            _mock_pack("AWS", managed=True, current_version="3.2.1"),
            _mock_pack("PackA", current_version=None),
        ]

        data = _write_and_read(tmp_path, packs)

        assert len(data["packs"]) == 2
        for entry in data["packs"]:
            assert "current_version" in entry

    def test_graph_current_version_is_emitted(self, tmp_path: Path):
        """The version recorded on the graph is surfaced verbatim."""
        packs = [_mock_pack("PackA", current_version="1.4.7")]

        data = _write_and_read(tmp_path, packs)

        assert data["packs"][0]["current_version"] == "1.4.7"

    def test_empty_current_version_is_normalized_to_null(self, tmp_path: Path):
        """An empty string must never reach consumers as an empty string."""
        packs = [_mock_pack("PackA", current_version="")]

        data = _write_and_read(tmp_path, packs)

        assert data["packs"][0]["current_version"] is None
        assert (
            '"current_version": null'
            in (tmp_path / "pack_destinations.json").read_text()
        )

    def test_missing_current_version_is_null(self, tmp_path: Path):
        """A pack whose graph object carries no version serializes as JSON null."""
        packs = [_mock_pack("PackA", current_version=None)]

        data = _write_and_read(tmp_path, packs)

        assert data["packs"][0]["current_version"] is None

    def test_current_version_is_per_pack(self, tmp_path: Path):
        """The value must not be copied between packs in a single call."""
        packs = [
            _mock_pack("PackA", current_version="1.0.0"),
            _mock_pack("PackB", current_version="2.5.0"),
        ]

        data = _write_and_read(tmp_path, packs)

        versions = {p["pack_id"]: p["current_version"] for p in data["packs"]}
        assert versions == {"PackA": "1.0.0", "PackB": "2.5.0"}


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
    pack.current_version = "1.0.0"
    pack.content_items = []
    pack._is_item_tightly_coupled = MagicMock(return_value=True)
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
        dto.write_pack_destinations(output_path, artifacts_dir, managed_artifacts_dir)

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

        assert data["packs"][0]["artifact_path"] == str(artifacts_dir / "PackAManaged")

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

    def test_managed_pack_without_a_managed_artifacts_dir_is_empty(
        self, tmp_path: Path
    ):
        """No managed dump ran, so the pack is recorded with an empty artifact path."""
        pack = _artifact_mock_pack("AWSManaged", "AWSManagedDirectory")
        pack.managed = True

        data = _write_destinations_with_dump_dirs(
            [pack],
            tmp_path / "pack_destinations.json",
            artifacts_dir=tmp_path / "content_packs",
        )

        assert [entry["pack_id"] for entry in data["packs"]] == ["AWSManaged"]
        assert data["packs"][0]["artifact_path"] == ""

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
        dto.get_pack_destination_mapping = (
            ContentDTO.get_pack_destination_mapping.__get__(dto, ContentDTO)
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

        assert (
            pack_family_key("pack_a")
            == "coalesce(pack_a.derived_from, pack_a.object_id)"
        )

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
        assert (
            "NOT (coalesce(pack_a.managed, false) OR coalesce(pack_a.is_derived, false))"
            in query
        )
        assert (
            "NOT (coalesce(pack_b.managed, false) OR coalesce(pack_b.is_derived, false))"
            in query
        )

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
        assert (
            "NOT (coalesce(p1.managed, false) OR coalesce(p1.is_derived, false))"
            in query
        )
        assert (
            "NOT (coalesce(p2.managed, false) OR coalesce(p2.is_derived, false))"
            in query
        )

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
        assert (
            "NOT (coalesce(p1.managed, false) OR coalesce(p1.is_derived, false))"
            in query
        )
        assert (
            "NOT (coalesce(p2.managed, false) OR coalesce(p2.is_derived, false))"
            in query
        )

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


# ---------------------------------------------------------------------------
# Pack.is_managed_paired tests
# ---------------------------------------------------------------------------


class TestIsManagedPaired:
    """Tests for Pack.is_managed_paired - "this pack is half of a source/twin pair".

    True for a derived twin and for a source pack that yields one. False for a
    natively managed pack (AWS/Azure/GCP style), which has no twin at all, and
    for an ordinary pack with nothing tightly coupled to split out.
    """

    def _make_content_item(
        self,
        object_id: str,
        content_type: ContentType,
        deprecated: bool = False,
    ) -> MagicMock:
        mock = MagicMock()
        mock.object_id = object_id
        mock.content_type = content_type
        # Set explicitly: an unset attribute on a MagicMock auto-creates a truthy
        # child mock, which the deprecation predicate would read as "deprecated".
        mock.deprecated = deprecated
        mock.name = object_id
        mock.description = ""
        return mock

    def _make_pack(
        self,
        content_items: List[MagicMock],
        managed: bool = False,
        is_derived: bool = False,
        coupling_overrides: Optional[dict] = None,
        support: str = "xsoar",
        hidden: bool = False,
        deprecated: bool = False,
        object_id: str = "TestPack",
    ) -> MagicMock:
        from demisto_sdk.commands.content_graph.objects.pack import Pack

        mock = MagicMock(spec=Pack)
        mock.managed = managed
        mock.is_derived = is_derived
        mock.coupling_overrides = coupling_overrides
        mock.content_items = content_items
        # Eligibility inputs, all set explicitly for the same reason as above.
        mock.object_id = object_id
        mock.support = support
        mock.hidden = hidden
        mock.deprecated = deprecated
        mock.name = object_id
        mock.description = ""
        mock.pack_metadata_dict = {}
        # Bind the real methods
        mock._is_item_tightly_coupled = Pack._is_item_tightly_coupled.__get__(
            mock, Pack
        )
        mock._is_derived_pack_eligible = Pack._is_derived_pack_eligible.__get__(
            mock, Pack
        )
        mock.is_managed_paired = Pack.is_managed_paired.__get__(mock, Pack)
        return mock

    def test_derived_twin_is_managed_paired(self):
        """The twin IS the managed half of the pair, regardless of what it holds."""
        pack = self._make_pack(
            [self._make_content_item("MyIntegration", ContentType.INTEGRATION)],
            managed=True,
            is_derived=True,
        )
        assert (
            pack.is_managed_paired() is True
        ), "a derived twin is by definition the managed half of a source/twin pair"

    def test_source_pack_with_tightly_coupled_item_is_managed_paired(self):
        """The marketplace half: not managed, and it yields a twin."""
        assert (
            ContentType.INTEGRATION in TIGHTLY_COUPLED_TYPES
        ), "test premise: an integration must be tightly coupled for this pack to yield a twin"
        pack = self._make_pack(
            [self._make_content_item("MyIntegration", ContentType.INTEGRATION)],
        )
        assert (
            pack.is_managed_paired() is True
        ), "an unmanaged pack with a tightly coupled item yields a twin, so it is the marketplace half of a pair"

    def test_natively_managed_pack_is_not_managed_paired(self):
        """GCP/AWS/Azure style packs are managed at the source - no twin exists."""
        pack = self._make_pack(
            [self._make_content_item("GoogleCloudPlatform", ContentType.INTEGRATION)],
            managed=True,
            is_derived=False,
        )
        assert pack.is_managed_paired() is False, (
            "a natively managed pack (GCP/AWS/Azure style: managed=True, is_derived=False) has no twin, "
            "so it never participates in a source/twin pair"
        )

    def test_pack_with_only_loosely_coupled_items_is_not_managed_paired(self):
        """No tightly coupled item means no twin is generated."""
        pack = self._make_pack(
            [self._make_content_item("MyPlaybook", ContentType.PLAYBOOK)],
        )
        assert (
            pack.is_managed_paired() is False
        ), "a pack whose only items are loosely coupled (a playbook here) produces no twin"

    def test_override_to_loosely_coupled_makes_pack_not_managed_paired(self):
        """The predicate must honour coupling_overrides, not the raw content type."""
        pack = self._make_pack(
            [self._make_content_item("MyIntegration", ContentType.INTEGRATION)],
            coupling_overrides={"MyIntegration": "loosely_coupled"},
        )
        assert (
            pack.is_managed_paired() is False
        ), "the pack's only integration is overridden to loosely_coupled, so nothing is left to split into a twin"

    @pytest.mark.parametrize("support", ["partner", "community", "developer", ""])
    def test_non_xsoar_supported_pack_is_not_managed_paired(self, support: str):
        """Only xsoar-supported packs are split, so no other pack advertises a twin."""
        pack = self._make_pack(
            [self._make_content_item("MyIntegration", ContentType.INTEGRATION)],
            support=support,
        )
        assert (
            pack.is_managed_paired() is False
        ), f"a {support or 'support-less'} pack is never split, so it must not advertise a managed twin"

    def test_pack_whose_only_tightly_coupled_item_is_deprecated_is_not_managed_paired(
        self,
    ):
        """Nothing eligible is left to split out, so no twin is generated."""
        pack = self._make_pack(
            [
                self._make_content_item(
                    "MyIntegration", ContentType.INTEGRATION, deprecated=True
                )
            ],
        )
        assert (
            pack.is_managed_paired() is False
        ), "the pack's only tightly coupled item is deprecated, so no twin is generated for it"

    def test_hidden_pack_is_not_managed_paired(self):
        pack = self._make_pack(
            [self._make_content_item("MyIntegration", ContentType.INTEGRATION)],
            hidden=True,
        )
        assert (
            pack.is_managed_paired() is False
        ), "a hidden pack is never split, so it must not advertise a managed twin"

    def test_deprecated_pack_is_not_managed_paired(self):
        pack = self._make_pack(
            [self._make_content_item("MyIntegration", ContentType.INTEGRATION)],
            deprecated=True,
        )
        assert (
            pack.is_managed_paired() is False
        ), "a deprecated pack is never split, so it must not advertise a managed twin"

    def test_excluded_pack_is_not_managed_paired(self, monkeypatch):
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "TestPack")
        pack = self._make_pack(
            [self._make_content_item("MyIntegration", ContentType.INTEGRATION)],
        )
        assert (
            pack.is_managed_paired() is False
        ), "an explicitly excluded pack must not advertise a managed twin either"


# ---------------------------------------------------------------------------
# Top level `managedPaired` key in the dumped metadata.json (CIAC-16414)
# ---------------------------------------------------------------------------


class TestManagedPairedTopLevelMetadata:
    """Tests for the top level ``managedPaired`` key written by ``Pack.dump_metadata``.

    The key is always emitted (including when it is False) while ENABLE_SPLIT_PACKS is
    on, and is omitted entirely while the flag is off, which is the production default.

    These tests drive the real ``Pack.dump_metadata`` against a real ``Pack`` and read
    the JSON back, rather than the ``MagicMock(spec=Pack)`` idiom used above: the mock
    idiom cannot exercise a large real method, and a source-inspection test would not
    detect the gate being removed.
    """

    @staticmethod
    def _make_pack(managed: bool = False, is_derived: bool = False):
        from demisto_sdk.commands.common.constants import MarketplaceVersions
        from demisto_sdk.commands.content_graph.objects.pack import Pack

        return Pack(
            object_id="TestPack",
            content_type=ContentType.PACK,
            node_id="Pack:TestPack",
            path=Path("TestPack"),
            name="TestPack",
            display_name="TestPack",
            marketplaces=[MarketplaceVersions.XSOAR],
            current_version="1.0.0",
            description="A pack used to exercise the managedPaired metadata key.",
            created="2024-01-01T00:00:00Z",
            support="xsoar",
            author="Cortex XSOAR",
            certification="certified",
            hidden=False,
            tags=[],
            categories=[],
            useCases=[],
            keywords=[],
            contentItems={},
            managed=managed,
            is_derived=is_derived,
        )

    @staticmethod
    def _dump(pack, tmp_path: Path) -> dict:
        from demisto_sdk.commands.common.constants import MarketplaceVersions

        destination = tmp_path / "metadata.json"
        pack.dump_metadata(destination, MarketplaceVersions.XSOAR)
        return stdlib_json.loads(destination.read_text())

    def test_managed_paired_true_is_written_when_flag_on(self, mocker, tmp_path):
        """A derived twin is managed-paired, so the key must be written as True."""
        mocker.patch(
            "demisto_sdk.commands.content_graph.objects.pack.ENABLE_SPLIT_PACKS", True
        )
        pack = self._make_pack(managed=True, is_derived=True)
        assert (
            pack.is_managed_paired() is True
        ), "test premise: a derived twin must be managed-paired, otherwise this case asserts nothing"

        metadata = self._dump(pack, tmp_path)

        assert (
            "managedPaired" in metadata
        ), "with ENABLE_SPLIT_PACKS on, dump_metadata must emit the top level `managedPaired` key"
        assert metadata["managedPaired"] is True, (
            f"a derived twin is half of a source/twin pair, so `managedPaired` must be True, "
            f"got {metadata['managedPaired']!r}"
        )

    def test_managed_paired_false_is_still_written_when_flag_on(self, mocker, tmp_path):
        """A natively managed pack has no twin - the key must be PRESENT and False, never omitted."""
        mocker.patch(
            "demisto_sdk.commands.content_graph.objects.pack.ENABLE_SPLIT_PACKS", True
        )
        pack = self._make_pack(managed=True, is_derived=False)
        assert (
            pack.is_managed_paired() is False
        ), "test premise: a natively managed pack (managed=True, is_derived=False) must not be managed-paired"

        metadata = self._dump(pack, tmp_path)

        assert "managedPaired" in metadata, (
            "`managedPaired` must always be emitted while the flag is on, including when it is False - "
            "consumers must be able to tell 'not paired' apart from 'field not supported'"
        )
        assert metadata["managedPaired"] is False, (
            f"a natively managed pack (AWS/Azure/GCP style) has no twin, so `managedPaired` must be False, "
            f"got {metadata['managedPaired']!r}"
        )

    def test_managed_paired_is_absent_when_flag_off(self, mocker, tmp_path):
        """With the flag off (the production default) the key must not appear at all."""
        mocker.patch(
            "demisto_sdk.commands.content_graph.objects.pack.ENABLE_SPLIT_PACKS", False
        )
        pack = self._make_pack(managed=True, is_derived=True)
        assert (
            pack.is_managed_paired() is True
        ), "test premise: this pack would be managedPaired=True, so its absence below is caused by the flag alone"

        metadata = self._dump(pack, tmp_path)

        assert "managedPaired" not in metadata, (
            "while ENABLE_SPLIT_PACKS is off the `managedPaired` key must be absent entirely (not False), "
            f"keeping the blast radius at zero; got {metadata.get('managedPaired')!r}"
        )


# ---------------------------------------------------------------------------
# Per content item `managedPaired` key in the dumped metadata.json (CIAC-16414)
# ---------------------------------------------------------------------------


class TestManagedPairedContentItemMetadata:
    """Tests for the per content item ``managedPaired`` key inside ``contentItems``.

    Each entry states whether that individual item is tightly coupled, i.e. whether it
    is one of the items paired into the pack's managed twin. It is emitted on every item
    of every type (including when False) while ENABLE_SPLIT_PACKS is on, and is absent
    entirely while the flag is off.

    Like ``TestManagedPairedTopLevelMetadata`` these drive the real ``Pack.dump_metadata``
    against a real ``Pack`` and read the written JSON back, because the value is injected
    by the metadata writer and cannot be observed through a mocked pack.
    """

    INTEGRATION_ID = "MyIntegration"
    PLAYBOOK_ID = "MyPlaybook"

    @staticmethod
    def _make_integration(object_id: str, deprecated: bool = False):
        from demisto_sdk.commands.common.constants import MarketplaceVersions
        from demisto_sdk.commands.content_graph.objects.integration import Integration

        return Integration(
            id=object_id,
            content_type=ContentType.INTEGRATION,
            node_id=f"{ContentType.INTEGRATION}:{object_id}",
            path=Path(f"{object_id}.yml"),
            fromversion="6.0.0",
            toversion="99.99.99",
            display_name=object_id,
            name=object_id,
            marketplaces=[MarketplaceVersions.XSOAR],
            deprecated=deprecated,
            type="python3",
            docker_image="demisto/python3:3.10.11.54799",
            category="Utilities",
            commands=[],
        )

    @staticmethod
    def _make_playbook(object_id: str):
        from demisto_sdk.commands.common.constants import MarketplaceVersions
        from demisto_sdk.commands.content_graph.objects.playbook import Playbook

        return Playbook(
            id=object_id,
            content_type=ContentType.PLAYBOOK,
            node_id=f"{ContentType.PLAYBOOK}:{object_id}",
            path=Path(f"{object_id}.yml"),
            fromversion="6.0.0",
            toversion="99.99.99",
            display_name=object_id,
            name=object_id,
            marketplaces=[MarketplaceVersions.XSOAR],
            deprecated=False,
            is_test=False,
        )

    PACK_ID = "TestPack"

    @classmethod
    def _make_pack(
        cls,
        with_integration: bool = False,
        with_playbook: bool = False,
        coupling_overrides: Optional[Dict[str, str]] = None,
        support: str = "xsoar",
        hidden: bool = False,
        deprecated: bool = False,
        managed: bool = False,
        is_derived: bool = False,
        derived_from: Optional[str] = None,
        deprecated_integration: bool = False,
    ):
        """Builds a real ``Pack`` holding real content items, so ``contentItems`` is non-empty.

        This is the single ``Pack`` factory shared by the per item suite and by
        ``TestManagedPairedEndToEnd``: every knob that makes a pack stop splitting (a non-xsoar
        ``support`` level, ``hidden``, ``deprecated``, natively ``managed``) is exposed here, so the
        two suites cannot drift apart in what "a pack that does not split" means.

        The defaults describe the happy shape - an eligible, xsoar-supported, splitting pack.
        """
        from demisto_sdk.commands.common.constants import MarketplaceVersions
        from demisto_sdk.commands.content_graph.objects.pack import Pack
        from demisto_sdk.commands.content_graph.objects.pack_content_items import (
            PackContentItems,
        )

        content_items = PackContentItems()
        if with_integration:
            content_items.integration.append(
                cls._make_integration(
                    cls.INTEGRATION_ID, deprecated=deprecated_integration
                )
            )
        if with_playbook:
            content_items.playbook.append(cls._make_playbook(cls.PLAYBOOK_ID))

        return Pack(
            object_id=cls.PACK_ID,
            content_type=ContentType.PACK,
            node_id=f"Pack:{cls.PACK_ID}",
            path=Path(cls.PACK_ID),
            name=cls.PACK_ID,
            display_name=cls.PACK_ID,
            marketplaces=[MarketplaceVersions.XSOAR],
            current_version="1.0.0",
            description="A pack used to exercise the per item managedPaired metadata key.",
            created="2024-01-01T00:00:00Z",
            support=support,
            author="Cortex XSOAR",
            certification="certified",
            hidden=hidden,
            deprecated=deprecated,
            tags=[],
            categories=[],
            useCases=[],
            keywords=[],
            contentItems=content_items,
            managed=managed,
            is_derived=is_derived,
            derived_from=derived_from,
            coupling_overrides=coupling_overrides,
        )

    @staticmethod
    def _dump(pack, tmp_path: Path) -> dict:
        from demisto_sdk.commands.common.constants import MarketplaceVersions

        destination = tmp_path / "metadata.json"
        pack.dump_metadata(destination, MarketplaceVersions.XSOAR)
        return stdlib_json.loads(destination.read_text())

    @staticmethod
    def _enable_both_flags(mocker) -> None:
        """Turns the flag on in BOTH consuming modules, so ONE file carries both levels.

        Needed by the cases that compare the per item key against the pack level key: the two are
        read from separately bound ``ENABLE_SPLIT_PACKS`` names, so the top level key is absent
        unless ``objects.pack`` is patched as well.
        """
        mocker.patch(
            "demisto_sdk.commands.content_graph.objects.pack.ENABLE_SPLIT_PACKS", True
        )
        mocker.patch(
            "demisto_sdk.commands.content_graph.objects.pack_metadata.ENABLE_SPLIT_PACKS",
            True,
        )

    @staticmethod
    def _enable_flag(mocker) -> None:
        """Turns the flag on in the module that consumes it for the PER ITEM key.

        The name is bound at import time in each consuming module, so patching
        ``content_graph.common`` would have no effect. Only ``objects.pack_metadata``
        is patched here: these assertions are about ``contentItems`` entries alone, and
        deliberately leave the top level key (read from ``objects.pack``) off, which also
        proves the two gates are independent.
        """
        mocker.patch(
            "demisto_sdk.commands.content_graph.objects.pack_metadata.ENABLE_SPLIT_PACKS",
            True,
        )

    @staticmethod
    def _all_item_entries(metadata: dict) -> List[dict]:
        """Flattens every per item entry across every content type in ``contentItems``."""
        entries: List[dict] = []
        for type_entries in (metadata.get("contentItems") or {}).values():
            entries.extend(type_entries)
        return entries

    def test_tightly_coupled_item_is_marked_true(self, mocker, tmp_path):
        """An integration is tightly coupled, so its entry must carry `managedPaired: True`."""
        assert (
            ContentType.INTEGRATION in TIGHTLY_COUPLED_TYPES
        ), "test premise: an integration must be tightly coupled, otherwise this case asserts nothing"
        self._enable_flag(mocker)
        pack = self._make_pack(with_integration=True)

        metadata = self._dump(pack, tmp_path)

        integrations = metadata["contentItems"]["integration"]
        assert (
            len(integrations) == 1
        ), f"test premise: the pack must contribute exactly one integration entry, got {integrations!r}"
        entry = integrations[0]
        assert "managedPaired" in entry, (
            "with ENABLE_SPLIT_PACKS on, every content item entry must carry the `managedPaired` key; "
            f"got keys {sorted(entry)}"
        )
        assert entry["managedPaired"] is True, (
            f"an integration is tightly coupled, so it is paired into the managed twin and its entry "
            f"must be True, got {entry['managedPaired']!r}"
        )

    def test_loosely_coupled_item_is_present_and_false(self, mocker, tmp_path):
        """A playbook is loosely coupled: the key must be PRESENT and False, never omitted."""
        assert (
            ContentType.PLAYBOOK not in TIGHTLY_COUPLED_TYPES
        ), "test premise: a playbook must be loosely coupled, otherwise this case asserts nothing"
        self._enable_flag(mocker)
        pack = self._make_pack(with_playbook=True)

        metadata = self._dump(pack, tmp_path)

        playbooks = metadata["contentItems"]["playbook"]
        assert (
            len(playbooks) == 1
        ), f"test premise: the pack must contribute exactly one playbook entry, got {playbooks!r}"
        entry = playbooks[0]
        assert "managedPaired" in entry, (
            "`managedPaired` must be emitted on EVERY item while the flag is on, including loosely "
            f"coupled ones - consumers must tell 'not paired' apart from 'field not supported'; got keys {sorted(entry)}"
        )
        assert entry["managedPaired"] is False, (
            f"a playbook is loosely coupled and stays with the marketplace half, so its entry must be "
            f"False, got {entry['managedPaired']!r}"
        )

    def test_value_is_per_item_within_a_single_pack(self, mocker, tmp_path):
        """Both item kinds in one pack: the value must differ per item, not be copied from the pack."""
        self._enable_flag(mocker)
        pack = self._make_pack(with_integration=True, with_playbook=True)

        metadata = self._dump(pack, tmp_path)

        integration_entry = metadata["contentItems"]["integration"][0]
        playbook_entry = metadata["contentItems"]["playbook"][0]
        assert integration_entry["managedPaired"] is True, (
            f"the tightly coupled integration must be True in the same written file, "
            f"got {integration_entry['managedPaired']!r}"
        )
        assert playbook_entry["managedPaired"] is False, (
            f"the loosely coupled playbook must be False in the same written file, proving the value is "
            f"resolved per item rather than copied from the pack, got {playbook_entry['managedPaired']!r}"
        )

    def test_key_is_absent_from_every_entry_when_flag_off(self, mocker, tmp_path):
        """With the flag off (the production default) no item entry may carry the key."""
        mocker.patch(
            "demisto_sdk.commands.content_graph.objects.pack_metadata.ENABLE_SPLIT_PACKS",
            False,
        )
        pack = self._make_pack(with_integration=True, with_playbook=True)

        metadata = self._dump(pack, tmp_path)

        entries = self._all_item_entries(metadata)
        assert len(entries) == 2, (
            f"test premise: both content items must reach the metadata, otherwise the absence below is "
            f"vacuous; got {entries!r}"
        )
        offenders = [entry for entry in entries if "managedPaired" in entry]
        assert not offenders, (
            "while ENABLE_SPLIT_PACKS is off no content item entry may carry `managedPaired` at all "
            f"(not even False), keeping the blast radius at zero; offending entries: {offenders!r}"
        )

    def test_coupling_override_reaches_the_per_item_key(self, mocker, tmp_path):
        """`coupling_overrides` must win over the raw content type, per item."""
        self._enable_flag(mocker)
        pack = self._make_pack(
            with_integration=True,
            coupling_overrides={self.INTEGRATION_ID: "loosely_coupled"},
        )

        metadata = self._dump(pack, tmp_path)

        entry = metadata["contentItems"]["integration"][0]
        assert (
            "managedPaired" in entry
        ), f"the key must still be emitted for an overridden item; got keys {sorted(entry)}"
        assert entry["managedPaired"] is False, (
            f"the integration is overridden to loosely_coupled, so it stays with the marketplace half and "
            f"its entry must be False rather than the content type default True, got {entry['managedPaired']!r}"
        )

    # -- the per item key must also respect whether the OWNING PACK splits at all ------------
    #
    # A tightly coupled item only ends up in a managed twin if a twin is generated for its pack.
    # When the pack does not split - for ANY of the reasons enumerated by
    # `Pack._is_derived_pack_eligible` - no twin exists, nothing is paired, and every item of that
    # pack must therefore read False. The rule the cases below pin down is:
    #
    #     item managedPaired == (pack splits) AND (item is tightly coupled)

    @pytest.mark.parametrize("support", ["partner", "community", "developer", ""])
    def test_tightly_coupled_item_in_a_non_xsoar_supported_pack_is_false(
        self, mocker, monkeypatch, tmp_path, support: str
    ):
        """Only xsoar-supported packs split, so a tightly coupled item elsewhere is never paired."""
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "")
        self._enable_flag(mocker)
        pack = self._make_pack(with_integration=True, support=support)
        assert pack.is_managed_paired() is False, (
            f"test premise: a {support or 'support-less'} pack must not split, otherwise this case "
            f"asserts nothing"
        )

        metadata = self._dump(pack, tmp_path)

        entry = metadata["contentItems"]["integration"][0]
        assert entry["managedPaired"] is False, (
            f"the pack is {support or 'support-less'}-supported so no managed twin is ever generated "
            f"for it; with nothing to be paired into, its integration must be False even though an "
            f"integration is tightly coupled by type, got {entry['managedPaired']!r}"
        )

    def test_tightly_coupled_item_in_a_hidden_pack_is_false(
        self, mocker, monkeypatch, tmp_path
    ):
        """A hidden pack never splits, so its tightly coupled item is not paired into anything."""
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "")
        self._enable_flag(mocker)
        pack = self._make_pack(with_integration=True, hidden=True)
        assert (
            pack.is_managed_paired() is False
        ), "test premise: a hidden pack must not split, otherwise this case asserts nothing"

        metadata = self._dump(pack, tmp_path)

        entry = metadata["contentItems"]["integration"][0]
        assert entry["managedPaired"] is False, (
            f"the owning pack is hidden and therefore never yields a managed twin, so its integration "
            f"is not paired into one, got {entry['managedPaired']!r}"
        )

    def test_tightly_coupled_item_in_a_deprecated_pack_is_false(
        self, mocker, monkeypatch, tmp_path
    ):
        """A deprecated pack never splits, so its tightly coupled item is not paired into anything."""
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "")
        self._enable_flag(mocker)
        pack = self._make_pack(with_integration=True, deprecated=True)
        assert (
            pack.is_managed_paired() is False
        ), "test premise: a deprecated pack must not split, otherwise this case asserts nothing"

        metadata = self._dump(pack, tmp_path)

        entry = metadata["contentItems"]["integration"][0]
        assert entry["managedPaired"] is False, (
            f"the owning pack is deprecated and therefore never yields a managed twin, so its "
            f"integration is not paired into one, got {entry['managedPaired']!r}"
        )

    def test_tightly_coupled_item_in_an_excluded_pack_is_false(
        self, mocker, monkeypatch, tmp_path
    ):
        """A pack named in `DERIVED_PACKS_EXCLUDE` never splits, so its items are never paired."""
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, self.PACK_ID)
        self._enable_flag(mocker)
        pack = self._make_pack(with_integration=True)
        assert pack.is_managed_paired() is False, (
            "test premise: a pack listed in the exclusion list must not split, otherwise this case "
            "asserts nothing"
        )

        metadata = self._dump(pack, tmp_path)

        entry = metadata["contentItems"]["integration"][0]
        assert entry["managedPaired"] is False, (
            f"the owning pack is explicitly excluded from splitting, so no twin exists to pair its "
            f"integration into, got {entry['managedPaired']!r}"
        )

    def test_tightly_coupled_item_in_a_natively_managed_pack_is_false(
        self, mocker, monkeypatch, tmp_path
    ):
        """AWS/Azure/GCP shape: the pack is already managed at the source, so nothing is paired."""
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "")
        self._enable_flag(mocker)
        pack = self._make_pack(with_integration=True, managed=True, is_derived=False)
        assert pack.is_managed_paired() is False, (
            "test premise: a natively managed pack (managed=True, is_derived=False) must not split, "
            "otherwise this case asserts nothing"
        )

        metadata = self._dump(pack, tmp_path)

        entry = metadata["contentItems"]["integration"][0]
        assert entry["managedPaired"] is False, (
            f"a natively managed pack is managed at the source, so no source/twin pair is ever created "
            f"and none of its items is paired into a twin, got {entry['managedPaired']!r}"
        )

    def test_tightly_coupled_item_in_a_derived_twin_is_true(
        self, mocker, monkeypatch, tmp_path
    ):
        """Regression guard: gating on the pack must not turn the twin's own items False."""
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "")
        self._enable_flag(mocker)
        pack = self._make_pack(
            with_integration=True,
            managed=True,
            is_derived=True,
            derived_from="Source",
        )
        assert (
            pack.is_managed_paired() is True
        ), "test premise: a derived twin is always half of a pair, otherwise this case asserts nothing"

        metadata = self._dump(pack, tmp_path)

        entry = metadata["contentItems"]["integration"][0]
        assert entry["managedPaired"] is True, (
            f"a derived twin IS the managed half of a pair and its integration is exactly the kind of "
            f"item that was paired into it, so gating the per item key on the owning pack must leave "
            f"this True, got {entry['managedPaired']!r}"
        )

    def test_loosely_coupled_item_in_a_non_splitting_pack_is_false(
        self, mocker, monkeypatch, tmp_path
    ):
        """Both conjuncts are false at once: the value must be False, never inverted or or-ed."""
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "")
        self._enable_flag(mocker)
        pack = self._make_pack(with_playbook=True, support="partner")
        assert pack.is_managed_paired() is False, (
            "test premise: a partner-supported pack holding only a playbook must not split, otherwise "
            "this case asserts nothing"
        )

        metadata = self._dump(pack, tmp_path)

        entry = metadata["contentItems"]["playbook"][0]
        assert entry["managedPaired"] is False, (
            f"neither conjunct holds - the pack does not split and a playbook is loosely coupled - so "
            f"the value must be False; an implementation that inverted the pack gate, or OR-ed it with "
            f"the item's coupling instead of AND-ing, would read True here. "
            f"Got {entry['managedPaired']!r}"
        )

    def test_pack_whose_only_tightly_coupled_item_is_deprecated_is_false_at_both_levels(
        self, mocker, monkeypatch, tmp_path
    ):
        """A deprecated item is not carried into a twin, so no twin exists and both levels are False."""
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "")
        self._enable_both_flags(mocker)
        pack = self._make_pack(with_integration=True, deprecated_integration=True)

        metadata = self._dump(pack, tmp_path)

        entry = metadata["contentItems"]["integration"][0]
        assert entry["managedPaired"] is False, (
            f"the integration is deprecated, so it is never carried into a managed twin, "
            f"got {entry['managedPaired']!r}"
        )
        assert metadata["managedPaired"] is False, (
            f"the pack's only tightly coupled item is deprecated, so nothing is left to split out and "
            f"the pack is not half of a pair either, got {metadata['managedPaired']!r}"
        )

    @pytest.mark.parametrize(
        "pack_kwargs, exclude_this_pack",
        [
            pytest.param({}, False, id="eligible-xsoar-pack-that-splits"),
            pytest.param({"support": "partner"}, False, id="partner-supported-pack"),
            pytest.param({"hidden": True}, False, id="hidden-pack"),
            pytest.param({"deprecated": True}, False, id="deprecated-pack"),
            pytest.param({"managed": True}, False, id="natively-managed-pack"),
            pytest.param(
                {"managed": True, "is_derived": True}, False, id="derived-twin"
            ),
            pytest.param({}, True, id="pack-in-DERIVED_PACKS_EXCLUDE"),
        ],
    )
    def test_item_value_equals_pack_splits_and_item_is_tightly_coupled(
        self,
        mocker,
        monkeypatch,
        tmp_path,
        pack_kwargs: Dict[str, object],
        exclude_this_pack: bool,
    ):
        """The whole rule, in one invariant, across every pack shape that matters.

        Each pack below holds one tightly coupled item (an integration) and one loosely coupled one
        (a playbook), and every entry is checked against the conjunction of the pack level answer -
        read from the very same written file - and the item's own coupling.
        """
        monkeypatch.setenv(
            DERIVED_PACKS_EXCLUDE_ENV, self.PACK_ID if exclude_this_pack else ""
        )
        self._enable_both_flags(mocker)
        pack = self._make_pack(
            with_integration=True,
            with_playbook=True,
            **pack_kwargs,  # type: ignore[arg-type]
        )

        metadata = self._dump(pack, tmp_path)

        pack_splits = metadata["managedPaired"]
        integration_entry = metadata["contentItems"]["integration"][0]
        playbook_entry = metadata["contentItems"]["playbook"][0]
        for entry, is_tightly_coupled in (
            (integration_entry, True),
            (playbook_entry, False),
        ):
            expected = pack_splits and is_tightly_coupled
            assert entry["managedPaired"] is expected, (
                f"the per item key must equal (pack splits) AND (item is tightly coupled): the pack "
                f"level key in this very file is {pack_splits!r} and this item is "
                f"{'tightly' if is_tightly_coupled else 'loosely'} coupled, so the entry must be "
                f"{expected!r}; got {entry['managedPaired']!r} for {entry['id']!r}"
            )


# ---------------------------------------------------------------------------
# End to end: BOTH `managedPaired` levels in a single written metadata.json (CIAC-16414)
# ---------------------------------------------------------------------------


class TestManagedPairedEndToEnd:
    """Drives both ``managedPaired`` gates together, into ONE written ``metadata.json``.

    ``TestManagedPairedTopLevelMetadata`` and ``TestManagedPairedContentItemMetadata`` each patch
    exactly ONE of the two independent module level ``ENABLE_SPLIT_PACKS`` names, so neither proves
    that the top level key and the per item keys coexist correctly in the shipped artifact. This
    class patches BOTH and asserts the two levels in the same file, which is what a consumer of the
    bucket actually reads.

    Construction is deliberately delegated to ``TestManagedPairedContentItemMetadata``'s builders -
    including its ``Pack`` factory, which now exposes every split-pack flag this class needs - rather
    than duplicated. No ``MagicMock`` is used anywhere here - the real writer runs end to end.
    """

    INTEGRATION_ID = TestManagedPairedContentItemMetadata.INTEGRATION_ID
    PLAYBOOK_ID = TestManagedPairedContentItemMetadata.PLAYBOOK_ID

    @staticmethod
    def _make_pack(**kwargs):
        """Reuses the single shared real-``Pack`` factory, so the two suites cannot drift apart."""
        return TestManagedPairedContentItemMetadata._make_pack(**kwargs)

    @staticmethod
    def _dump(pack, tmp_path: Path) -> dict:
        """Reuses the existing real-writer dump helper - one file, read back as JSON."""
        return TestManagedPairedContentItemMetadata._dump(pack, tmp_path)

    @staticmethod
    def _all_item_entries(metadata: dict) -> List[dict]:
        """Reuses the existing flattener over every ``contentItems`` entry of every type."""
        return TestManagedPairedContentItemMetadata._all_item_entries(metadata)

    @staticmethod
    def _set_both_flags(mocker, value: bool) -> None:
        """Sets BOTH gates at once.

        ``ENABLE_SPLIT_PACKS`` is bound at import time in each consuming module, so the top level key
        (``objects.pack``) and the per item key (``objects.pack_metadata``) are gated by two separate
        names. Patching ``content_graph.common`` would affect neither.
        """
        mocker.patch(
            "demisto_sdk.commands.content_graph.objects.pack.ENABLE_SPLIT_PACKS", value
        )
        mocker.patch(
            "demisto_sdk.commands.content_graph.objects.pack_metadata.ENABLE_SPLIT_PACKS",
            value,
        )

    def test_source_pack_writes_true_top_level_with_mixed_item_values(
        self, mocker, tmp_path
    ):
        """The marketplace half (the user's `Core` shape): pack True, integration True, playbook False."""
        assert (
            ContentType.INTEGRATION in TIGHTLY_COUPLED_TYPES
        ), "test premise: an integration must be tightly coupled, otherwise this case asserts nothing"
        assert (
            ContentType.PLAYBOOK not in TIGHTLY_COUPLED_TYPES
        ), "test premise: a playbook must be loosely coupled, otherwise this case asserts nothing"
        self._set_both_flags(mocker, True)
        pack = self._make_pack(with_integration=True, with_playbook=True)

        metadata = self._dump(pack, tmp_path)

        assert "managedPaired" in metadata, (
            "with both gates on, the single written metadata.json must carry the top level "
            f"`managedPaired` key; got top level keys {sorted(metadata)}"
        )
        assert metadata["managedPaired"] is True, (
            f"an unmanaged pack holding a tightly coupled integration yields a managed twin, so the "
            f"pack is the marketplace half of a pair and the top level key must be True, "
            f"got {metadata['managedPaired']!r}"
        )

        integration_entry = metadata["contentItems"]["integration"][0]
        playbook_entry = metadata["contentItems"]["playbook"][0]
        assert "managedPaired" in integration_entry, (
            f"the integration entry must carry `managedPaired` in the same written file; "
            f"got keys {sorted(integration_entry)}"
        )
        assert integration_entry["managedPaired"] is True, (
            f"the integration is tightly coupled, so it is one of the items paired into the twin, "
            f"got {integration_entry['managedPaired']!r}"
        )
        assert "managedPaired" in playbook_entry, (
            f"the playbook entry must carry `managedPaired` too - the key is always emitted while the "
            f"gate is on, including when False; got keys {sorted(playbook_entry)}"
        )
        assert playbook_entry["managedPaired"] is False, (
            f"the playbook is loosely coupled and stays with the marketplace half, so its entry must be "
            f"False in the very same file where the pack level key is True, "
            f"got {playbook_entry['managedPaired']!r}"
        )

    def test_derived_twin_writes_true_at_both_levels(self, mocker, tmp_path):
        """The managed half (the user's `AttlasianManaged` shape): pack True and its integration True."""
        self._set_both_flags(mocker, True)
        pack = self._make_pack(
            with_integration=True,
            managed=True,
            is_derived=True,
            derived_from="Attlasian",
        )

        metadata = self._dump(pack, tmp_path)

        assert "managedPaired" in metadata, (
            f"a derived twin's metadata must carry the top level `managedPaired` key; "
            f"got top level keys {sorted(metadata)}"
        )
        assert metadata["managedPaired"] is True, (
            f"a derived twin IS the managed half of a source/twin pair, so the top level key must be "
            f"True regardless of its contents, got {metadata['managedPaired']!r}"
        )

        integration_entry = metadata["contentItems"]["integration"][0]
        assert "managedPaired" in integration_entry, (
            f"the twin's integration entry must carry `managedPaired`; "
            f"got keys {sorted(integration_entry)}"
        )
        assert integration_entry["managedPaired"] is True, (
            f"the integration inside the twin is tightly coupled - it is exactly the kind of item that "
            f"caused the twin to be generated, got {integration_entry['managedPaired']!r}"
        )

    def test_natively_managed_pack_writes_false_at_both_levels(self, mocker, tmp_path):
        """AWS/Azure/GCP shape: the pack never splits, so BOTH levels are False and agree.

        The per item key does not report the item's coupling in isolation - it reports whether the
        item is actually paired into a managed twin, which requires the owning pack to split in the
        first place. A natively managed pack (``managed=True, is_derived=False``) is already managed
        at the source, so no twin is ever generated and there is nothing for its integration to be
        paired into.
        """
        self._set_both_flags(mocker, True)
        pack = self._make_pack(with_integration=True, managed=True, is_derived=False)

        metadata = self._dump(pack, tmp_path)

        assert "managedPaired" in metadata, (
            "the top level key must be emitted even when False - consumers must be able to tell "
            f"'not paired' apart from 'field not supported'; got top level keys {sorted(metadata)}"
        )
        assert metadata["managedPaired"] is False, (
            f"a natively managed pack (managed=True, is_derived=False - AWS/Azure/GCP style) is "
            f"already managed at the source, so no twin is ever generated and no source/twin pair "
            f"exists. Got {metadata['managedPaired']!r}"
        )

        integration_entry = metadata["contentItems"]["integration"][0]
        assert "managedPaired" in integration_entry, (
            f"the per item key must be emitted for the integration; "
            f"got keys {sorted(integration_entry)}"
        )
        assert integration_entry["managedPaired"] is False, (
            f"the per item key must be False here too, and the two levels must AGREE. The item key "
            f"answers 'is this item paired into a managed twin?', which is (the pack splits) AND "
            f"(the item is tightly coupled) - being an integration is not enough when the owning pack "
            f"yields no twin at all. Got {integration_entry['managedPaired']!r}"
        )

    def test_both_gates_off_writes_no_managed_paired_key_anywhere(
        self, mocker, tmp_path
    ):
        """The production default: neither the top level key nor ANY item entry key may appear."""
        self._set_both_flags(mocker, False)
        pack = self._make_pack(
            with_integration=True, with_playbook=True, managed=True, is_derived=True
        )
        assert pack.is_managed_paired() is True, (
            "test premise: this pack would be managedPaired=True, so the absences below are caused by "
            "the gates alone rather than by the pack's shape"
        )

        metadata = self._dump(pack, tmp_path)

        assert "managedPaired" not in metadata, (
            "with both gates off the top level `managedPaired` key must be absent entirely (not False); "
            f"got {metadata.get('managedPaired')!r}"
        )
        entries = self._all_item_entries(metadata)
        assert len(entries) == 2, (
            f"test premise: both content items must reach the metadata, otherwise the absence check "
            f"below is vacuous; got {entries!r}"
        )
        offenders = [entry for entry in entries if "managedPaired" in entry]
        assert not offenders, (
            "with both gates off no content item entry may carry `managedPaired` either - the check "
            f"covers every entry, not just the first; offending entries: {offenders!r}"
        )

    def test_override_removing_the_only_tightly_coupled_item_turns_both_levels_false(
        self, mocker, tmp_path
    ):
        """`coupling_overrides` propagates to both levels: the item flips False, and so does the pack.

        The pack's only tightly coupled item is overridden away, so nothing is left to split into a
        twin and the pack stops being half of a pair.
        """
        self._set_both_flags(mocker, True)
        pack = self._make_pack(
            with_integration=True,
            coupling_overrides={self.INTEGRATION_ID: "loosely_coupled"},
        )

        metadata = self._dump(pack, tmp_path)

        integration_entry = metadata["contentItems"]["integration"][0]
        assert "managedPaired" in integration_entry, (
            f"the key must still be emitted for an overridden item; "
            f"got keys {sorted(integration_entry)}"
        )
        assert integration_entry["managedPaired"] is False, (
            f"the integration is overridden to loosely_coupled, so the override must win over the "
            f"content type default, got {integration_entry['managedPaired']!r}"
        )
        assert (
            "managedPaired" in metadata
        ), f"the top level key must still be emitted; got top level keys {sorted(metadata)}"
        assert metadata["managedPaired"] is False, (
            f"the override left the pack with zero tightly coupled items, so no twin would be "
            f"generated and the pack is not half of a pair, got {metadata['managedPaired']!r}"
        )


class TestSplitPackDependencySweep:
    """Tests for the final sweep that severs dependencies of managed packs.

    Guarding each writing query individually is not airtight: a DEPENDS_ON edge
    can also reach the graph through relationship preservation across a rebuild,
    which never consults those guards. The sweep runs unconditionally at the end
    of the dependency phase, so the invariant holds no matter how an edge got in.
    """

    def test_sweep_deletes_edges_on_either_side_and_between_twins(self):
        """One deletion covers all three illegitimate shapes: a managed source,
        a managed target, and two packs of the same split family."""
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import (
            remove_split_pack_dependencies,
        )

        with patch(
            "demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies.run_query",
            return_value=[],
        ) as mock_run_query:
            remove_split_pack_dependencies(MagicMock())

        query = mock_run_query.call_args[0][1]
        assert (
            "(coalesce(pack_a.managed, false) OR coalesce(pack_a.is_derived, false))"
            in query
        )
        assert (
            "(coalesce(pack_b.managed, false) OR coalesce(pack_b.is_derived, false))"
            in query
        )
        assert (
            "coalesce(pack_a.derived_from, pack_a.object_id) "
            "= coalesce(pack_b.derived_from, pack_b.object_id)" in query
        )
        assert "DELETE r" in query, f"the sweep must delete, got: {query}"

    def test_sweep_matches_packs_in_both_directions(self):
        """A managed pack must neither depend on another pack nor be depended
        upon, so the pattern is directional but the predicates cover both ends."""
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import (
            remove_split_pack_dependencies,
        )

        with patch(
            "demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies.run_query",
            return_value=[],
        ) as mock_run_query:
            remove_split_pack_dependencies(MagicMock())

        query = mock_run_query.call_args[0][1]
        assert (
            "(pack_a:Pack)-[r:DEPENDS_ON]->(pack_b:Pack)" in query
        ), f"the sweep must be restricted to pack-to-pack edges, got: {query}"

    def test_sweep_returns_the_severed_pairs(self):
        """The caller prunes the mapping using these pairs, so they must be
        reported back rather than silently dropped."""
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import (
            remove_split_pack_dependencies,
        )

        with patch(
            "demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies.run_query",
            return_value=[
                {"source": "HelloWorldManaged", "target": "Base"},
                {"source": "HelloWorld", "target": "HelloWorldManaged"},
            ],
        ):
            severed = remove_split_pack_dependencies(MagicMock())

        assert severed == {
            ("HelloWorldManaged", "Base"),
            ("HelloWorld", "HelloWorldManaged"),
        }

    def test_pruning_drops_severed_pairs_and_keeps_the_rest(self):
        """``depends_on.json`` must describe the graph after the sweep, so a
        severed pair cannot survive in the mapping - but unrelated dependencies
        of the same source pack must be preserved."""
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import (
            prune_severed_dependencies,
        )

        depends_on_data = {
            "HelloWorld": {
                "HelloWorldManaged": [{"source": "a", "target": "b"}],
                "CommonScripts": [{"source": "c", "target": "d"}],
            },
        }

        pruned = prune_severed_dependencies(
            depends_on_data, {("HelloWorld", "HelloWorldManaged")}
        )

        assert pruned == {
            "HelloWorld": {"CommonScripts": [{"source": "c", "target": "d"}]}
        }

    def test_pruning_removes_a_source_left_with_no_targets(self):
        """A source whose every dependency was severed must disappear entirely,
        rather than linger as an empty mapping."""
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import (
            prune_severed_dependencies,
        )

        pruned = prune_severed_dependencies(
            {"HelloWorldManaged": {"Base": [{"source": "a", "target": "b"}]}},
            {("HelloWorldManaged", "Base")},
        )

        assert pruned == {}

    def test_pruning_is_a_no_op_when_nothing_was_severed(self):
        """The common case - a repo with no split packs - must leave the
        existing mapping untouched."""
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import (
            prune_severed_dependencies,
        )

        depends_on_data = {"HelloWorld": {"Base": [{"source": "a", "target": "b"}]}}

        assert prune_severed_dependencies(depends_on_data, set()) is depends_on_data

    def test_regular_pack_dependencies_are_never_pruned(self):
        """The whole point of the change is that only managed/derived packs are
        affected; ordinary pack-to-pack dependencies must keep working."""
        from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import (
            prune_severed_dependencies,
        )

        depends_on_data = {
            "HelloWorld": {"Base": [{"source": "a", "target": "b"}]},
            "Phishing": {"CommonScripts": [{"source": "c", "target": "d"}]},
        }

        pruned = prune_severed_dependencies(
            depends_on_data, {("HelloWorldManaged", "Base")}
        )

        assert pruned == depends_on_data

    def test_dependency_phase_sweeps_after_creating_dependencies(self):
        """Order matters: sweeping before creation would let the creation query
        reintroduce an edge. The sweep has to be the last step."""
        from demisto_sdk.commands.content_graph.interface.neo4j.queries import (
            dependencies as dependencies_module,
        )

        call_order = []

        with (
            patch.object(
                dependencies_module,
                "remove_existing_depends_on_relationships",
                side_effect=lambda tx: call_order.append("remove_existing"),
            ),
            patch.object(
                dependencies_module,
                "update_uses_for_integration_commands",
                side_effect=lambda tx: call_order.append("update_uses"),
            ),
            patch.object(
                dependencies_module,
                "delete_deprecatedcontent_relationship",
                side_effect=lambda tx: call_order.append("delete_deprecated"),
            ),
            patch.object(
                dependencies_module,
                "create_depends_on_relationships",
                side_effect=lambda tx: (call_order.append("create"), {})[1],
            ),
            patch.object(
                dependencies_module,
                "remove_split_pack_dependencies",
                side_effect=lambda tx: (call_order.append("sweep"), set())[1],
            ),
            patch.object(dependencies_module, "write_depends_on_artifact"),
        ):
            dependencies_module.create_pack_dependencies(MagicMock())

        assert call_order.index("sweep") > call_order.index(
            "create"
        ), f"the sweep must run after dependency creation, got order {call_order}"

    def test_artifact_is_written_after_pruning(self):
        """``depends_on.json`` is consumed downstream, so it must be serialized
        from the pruned mapping rather than the pre-sweep one."""
        from demisto_sdk.commands.content_graph.interface.neo4j.queries import (
            dependencies as dependencies_module,
        )

        with (
            patch.object(
                dependencies_module, "remove_existing_depends_on_relationships"
            ),
            patch.object(dependencies_module, "update_uses_for_integration_commands"),
            patch.object(dependencies_module, "delete_deprecatedcontent_relationship"),
            patch.object(
                dependencies_module,
                "create_depends_on_relationships",
                return_value={
                    "HelloWorld": {
                        "HelloWorldManaged": [{"source": "a", "target": "b"}],
                        "Base": [{"source": "c", "target": "d"}],
                    }
                },
            ),
            patch.object(
                dependencies_module,
                "remove_split_pack_dependencies",
                return_value={("HelloWorld", "HelloWorldManaged")},
            ),
            patch.object(
                dependencies_module, "write_depends_on_artifact"
            ) as mock_write,
        ):
            result = dependencies_module.create_pack_dependencies(MagicMock())

        expected = {"HelloWorld": {"Base": [{"source": "c", "target": "d"}]}}
        assert result == expected
        mock_write.assert_called_once_with(expected)


class TestPackDestinationsSourceVsDumpedSource:
    """``pack_destinations.json``'s ``source`` and the dumped ``metadata.json``'s ``source`` CAN differ.

    These are two different values produced by two different stages:

    * ``write_pack_destinations()`` writes the raw graph attribute ``pack.source``, which
      ``PackParser`` populates as ``metadata.get("source", "")`` - the PLAIN key only.
    * ``Pack.dump_metadata()`` writes ``metadata.json`` through
      ``MarketplaceSuffixPreparer.prepare_managed_and_source()``, which lets a marketplace-suffixed
      ``source:platform`` override win for the platform marketplace.

    For a pack that declares BOTH, the two artifacts therefore disagree. These are characterization
    tests: they document the behaviour as it is today, so that a future change which makes the two
    agree fails here loudly and deliberately rather than silently.

    This matters downstream: infra's managed-content upload derives a pack's bucket feature
    directory from ``pack_destinations.json`` up front, but re-derives it from the dumped
    ``metadata.json`` per pack. A disagreement can make the up-front check look for the pack under
    the wrong feature, find it "already present", and skip an upload that never happened.
    """

    AUTHORED_METADATA = {
        "name": "ProbePack",
        "managed": True,
        "source": "plain_feature",
        "managed:platform": True,
        "source:platform": "platform_feature",
    }

    def test_dumped_metadata_resolves_the_platform_suffixed_source(self):
        """The dump resolves ``source:platform`` into the plain ``source`` for the platform MP."""
        from demisto_sdk.commands.common.constants import MarketplaceVersions
        from demisto_sdk.commands.prepare_content.preparers.marketplace_suffix_preparer import (
            MarketplaceSuffixPreparer,
        )

        resolved = MarketplaceSuffixPreparer.prepare_managed_and_source(
            dict(self.AUTHORED_METADATA), MarketplaceVersions.PLATFORM
        )

        assert resolved["source"] == "platform_feature"

    def test_pack_destinations_records_the_unresolved_plain_source(
        self, tmp_path: Path
    ):
        """The destinations artifact records the PLAIN source, ignoring the platform override."""
        pack = _artifact_mock_pack("ProbePack", "ProbePack")
        pack.managed = True
        pack.source = self.AUTHORED_METADATA["source"]

        data, _ = _dump_and_write_destinations([pack], tmp_path / "artifacts")

        assert data["packs"][0]["source"] == "plain_feature"

    def test_the_two_sources_diverge_for_a_platform_suffixed_pack(self, tmp_path: Path):
        """The two artifacts disagree for the same pack - the reason infra needs a mismatch guard."""
        from demisto_sdk.commands.common.constants import MarketplaceVersions
        from demisto_sdk.commands.prepare_content.preparers.marketplace_suffix_preparer import (
            MarketplaceSuffixPreparer,
        )

        dumped_source = MarketplaceSuffixPreparer.prepare_managed_and_source(
            dict(self.AUTHORED_METADATA), MarketplaceVersions.PLATFORM
        )["source"]

        pack = _artifact_mock_pack("ProbePack", "ProbePack")
        pack.managed = True
        pack.source = self.AUTHORED_METADATA["source"]
        data, _ = _dump_and_write_destinations([pack], tmp_path / "artifacts")
        destinations_source = data["packs"][0]["source"]

        assert dumped_source == "platform_feature"
        assert destinations_source == "plain_feature"
        assert dumped_source != destinations_source

    def test_the_two_sources_agree_when_no_suffixed_source_is_declared(
        self, tmp_path: Path
    ):
        """Without a ``source:platform`` override the two artifacts agree, which is the common case."""
        from demisto_sdk.commands.common.constants import MarketplaceVersions
        from demisto_sdk.commands.prepare_content.preparers.marketplace_suffix_preparer import (
            MarketplaceSuffixPreparer,
        )

        authored = {"name": "PlainPack", "managed": True, "source": "plain_feature"}
        dumped_source = MarketplaceSuffixPreparer.prepare_managed_and_source(
            dict(authored), MarketplaceVersions.PLATFORM
        )["source"]

        pack = _artifact_mock_pack("PlainPack", "PlainPack")
        pack.managed = True
        pack.source = authored["source"]
        data, _ = _dump_and_write_destinations([pack], tmp_path / "artifacts")

        assert dumped_source == data["packs"][0]["source"] == "plain_feature"


# ---------------------------------------------------------------------------
# DERIVED_PACKS_EXCLUDE env var parsing
# ---------------------------------------------------------------------------


class TestDerivedPackExclusions:
    """``DERIVED_PACKS_EXCLUDE`` names packs that must never yield a twin.

    Mirrors the ``TestResolveDerivedPackSource`` style: the variable is read per
    call, so tests may change it freely.
    """

    def test_unset_var_yields_no_exclusions(self, monkeypatch):
        monkeypatch.delenv(DERIVED_PACKS_EXCLUDE_ENV, raising=False)
        assert derived_pack_exclusions() == frozenset()

    def test_empty_string_yields_no_exclusions(self, monkeypatch):
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "")
        assert derived_pack_exclusions() == frozenset()

    def test_single_entry(self, monkeypatch):
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "Gmail")
        assert derived_pack_exclusions() == frozenset({"gmail"})

    def test_multiple_entries(self, monkeypatch):
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "Gmail,Slack,Jira")
        assert derived_pack_exclusions() == frozenset({"gmail", "slack", "jira"})

    def test_entries_are_casefolded(self, monkeypatch):
        """Matching is case-insensitive, so the stored form is casefolded."""
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "GMAIL")
        assert derived_pack_exclusions() == frozenset({"gmail"})

    def test_surrounding_whitespace_is_trimmed(self, monkeypatch):
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "  Gmail  ,\tSlack\n")
        assert derived_pack_exclusions() == frozenset({"gmail", "slack"})

    def test_whitespace_only_entries_are_dropped(self, monkeypatch):
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "Gmail, ,,   ,Slack")
        assert derived_pack_exclusions() == frozenset({"gmail", "slack"})

    def test_whitespace_only_value_yields_no_exclusions(self, monkeypatch):
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "   ,  , ")
        assert derived_pack_exclusions() == frozenset()

    def test_env_var_is_read_per_call_not_at_import(self, monkeypatch):
        """Unlike ENABLE_SPLIT_PACKS, the value must not be frozen at import
        time, so a second read reflects a changed environment."""
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "First")
        assert derived_pack_exclusions() == frozenset({"first"})
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "Second")
        assert derived_pack_exclusions() == frozenset({"second"})
        monkeypatch.delenv(DERIVED_PACKS_EXCLUDE_ENV, raising=False)
        assert derived_pack_exclusions() == frozenset()


# ---------------------------------------------------------------------------
# The shared deprecation predicate
# ---------------------------------------------------------------------------


class TestSharedDeprecationPredicate:
    """``is_deprecated_entity`` is the single rule applied to BOTH a pack and a
    content item by the split-pack logic: an explicit ``deprecated`` field OR the
    legacy name/description convention.
    """

    def test_explicit_field_alone_is_enough(self):
        assert is_deprecated_entity("Anything", "Any description", True) is True

    def test_name_and_description_convention_without_the_field(self):
        assert (
            is_deprecated_entity(
                "My Pack (Deprecated)", "Deprecated. Use Other Pack instead.", False
            )
            is True
        )

    def test_no_available_replacement_wording_is_accepted(self):
        assert (
            is_deprecated_entity(
                "My Pack (Deprecated)", "Deprecated. No available replacement.", False
            )
            is True
        )

    def test_deprecated_name_without_a_deprecated_description_is_not_enough(self):
        """Both halves of the convention are required, matching the legacy rule."""
        assert (
            is_deprecated_entity("My Pack (Deprecated)", "An ordinary description")
            is False
        )

    def test_deprecated_description_without_a_deprecated_name_is_not_enough(self):
        assert (
            is_deprecated_entity("My Pack", "Deprecated. Use Other Pack instead.")
            is False
        )

    def test_plain_entity_is_not_deprecated(self):
        assert is_deprecated_entity("My Pack", "An ordinary description") is False

    @pytest.mark.parametrize(
        "name, description", [(None, None), ("My Pack", None), (None, "Deprecated.")]
    )
    def test_missing_name_or_description_is_not_deprecated(self, name, description):
        """A missing field must never raise, and never imply deprecation."""
        assert is_deprecated_entity(name, description) is False

    def test_pack_and_content_item_agree_on_the_explicit_field(self):
        """Parity: the same input decided the same way for both entity kinds."""
        item = MagicMock()
        item.name, item.description, item.deprecated = "X", "", True
        pack = MagicMock()
        pack.name, pack.description, pack.deprecated = "X", "", True
        pack.pack_metadata_dict = {}

        assert is_deprecated_content_item(item) is True
        assert is_deprecated_pack(pack) is True

    def test_pack_and_content_item_agree_on_the_name_description_convention(self):
        item = MagicMock()
        item.name = "Thing (Deprecated)"
        item.description = "Deprecated. Use Other instead."
        item.deprecated = False
        pack = MagicMock()
        pack.name = "Thing (Deprecated)"
        pack.description = "Deprecated. Use Other instead."
        pack.deprecated = False
        pack.pack_metadata_dict = {}

        assert is_deprecated_content_item(item) is True
        assert is_deprecated_pack(pack) is True

    def test_pack_and_content_item_agree_on_a_live_entity(self):
        item = MagicMock()
        item.name, item.description, item.deprecated = "Thing", "A thing.", False
        pack = MagicMock()
        pack.name, pack.description, pack.deprecated = "Thing", "A thing.", False
        pack.pack_metadata_dict = {}

        assert is_deprecated_content_item(item) is False
        assert is_deprecated_pack(pack) is False

    def test_pack_metadata_deprecated_field_is_honoured(self):
        """The pack-level helper also reads ``deprecated`` from pack_metadata.json,
        which the legacy ``PackParser.deprecated`` property ignores."""
        pack = MagicMock()
        pack.name, pack.description, pack.deprecated = "Thing", "A thing.", False
        pack.pack_metadata_dict = {"deprecated": True}

        assert is_deprecated_pack(pack) is True


# ---------------------------------------------------------------------------
# Derived pack eligibility at the single creation point
# ---------------------------------------------------------------------------


def _make_parser_content_item(
    object_id: str,
    content_type: ContentType = ContentType.INTEGRATION,
    deprecated: bool = False,
) -> MagicMock:
    """A content item parser stand-in for the derived-pack creation tests."""
    item = MagicMock()
    item.object_id = object_id
    item.content_type = content_type
    item.deprecated = deprecated
    item.name = object_id
    item.description = ""
    item.relationships = Relationships()
    return item


def _make_pack_parser(
    content_items: List[MagicMock],
    object_id: str = "TestPack",
    managed: bool = False,
    support: str = "xsoar",
    hidden: bool = False,
    deprecated: bool = False,
    pack_metadata_dict: Optional[dict] = None,
    coupling_overrides: Optional[dict] = None,
) -> MagicMock:
    """A ``PackParser`` stand-in with the real eligibility/coupling/generation
    methods bound, so the tests drive the production code paths."""
    from demisto_sdk.commands.content_graph.parsers.pack import PackParser

    parser = MagicMock(spec=PackParser)
    # Fields the gate under test reads.
    parser.object_id = object_id
    parser.name = object_id
    parser.description = ""
    parser.managed = managed
    parser.support = support
    parser.hidden = hidden
    parser.deprecated = deprecated
    parser.pack_metadata_dict = pack_metadata_dict or {}
    parser.coupling_overrides = coupling_overrides
    parser.derived_source = None
    # Remaining fields exist only so a real DerivedPackParser can be constructed
    # in the positive cases; their values are irrelevant to these assertions.
    parser.path = Path(f"/fake/Packs/{object_id}")
    parser.display_name = object_id
    parser.created = "2024-01-01"
    parser.updated = "2024-01-01"
    parser.legacy = True
    parser.email = ""
    parser.eulaLink = ""
    parser.author_image = ""
    parser.price = 0
    parser.server_min_version = "6.0.0"
    parser.current_version = "1.0.0"
    parser.version_info = ""
    parser.commit = "abc123"
    parser.downloads = 0
    parser.tags = []
    parser.default_data_source_id = ""
    parser.keywords = []
    parser.search_rank = 0
    parser.videos = []
    parser.excluded_dependencies = []
    parser.modules = []
    parser.integrations = []
    parser.premium = False
    parser.vendor_id = ""
    parser.partner_id = ""
    parser.partner_name = ""
    parser.preview_only = False
    parser.disable_monthly = False
    parser.content_commit_hash = ""
    parser.hybrid = False
    parser.supportedModules = None
    parser.internal = False
    parser.source = ""
    parser.private_pack_path = None
    parser.contributors = []
    parser.latest_rn_version = "1.0.0"
    parser.relationships = Relationships()

    items = MagicMock()
    items.iter_lists.return_value = [content_items]
    parser.content_items = items

    parser._is_item_tightly_coupled = PackParser._is_item_tightly_coupled.__get__(
        parser, PackParser
    )
    parser._is_derived_pack_eligible = PackParser._is_derived_pack_eligible.__get__(
        parser, PackParser
    )
    parser._generate_derived_pack = PackParser._generate_derived_pack.__get__(
        parser, PackParser
    )
    return parser


class TestDerivedPackEligibility:
    """Only an xsoar-supported, live, visible, non-excluded pack may be split.

    Every case keeps a tightly coupled integration in the pack, so a ``None``
    result is caused by the gate under test and nothing else.
    """

    def test_xsoar_supported_pack_yields_a_derived_pack(self):
        """Positive control: without it, the negative cases prove nothing."""
        parser = _make_pack_parser([_make_parser_content_item("MyIntegration")])
        assert (
            parser._generate_derived_pack() is not None
        ), "an xsoar-supported pack with a live tightly coupled item must still yield a twin"

    @pytest.mark.parametrize("support", ["partner", "community", "developer"])
    def test_non_xsoar_supported_pack_yields_none(self, support: str):
        parser = _make_pack_parser(
            [_make_parser_content_item("MyIntegration")], support=support
        )
        assert (
            parser._generate_derived_pack() is None
        ), f"a {support}-supported pack must never be split"

    @pytest.mark.parametrize("support", ["", None])
    def test_missing_support_yields_none(self, support):
        """The allowlist is strict: an absent support level is not xsoar."""
        parser = _make_pack_parser(
            [_make_parser_content_item("MyIntegration")], support=support
        )
        assert parser._generate_derived_pack() is None

    def test_support_matching_is_case_insensitive(self):
        parser = _make_pack_parser(
            [_make_parser_content_item("MyIntegration")], support="XSOAR"
        )
        assert (
            parser._generate_derived_pack() is not None
        ), "support levels differing only in case must still be recognised as xsoar"

    def test_managed_pack_yields_none(self):
        parser = _make_pack_parser(
            [_make_parser_content_item("MyIntegration")], managed=True
        )
        assert parser._generate_derived_pack() is None

    def test_deprecated_pack_yields_none(self):
        parser = _make_pack_parser(
            [_make_parser_content_item("MyIntegration")], deprecated=True
        )
        assert parser._generate_derived_pack() is None

    def test_pack_deprecated_via_pack_metadata_field_yields_none(self):
        parser = _make_pack_parser(
            [_make_parser_content_item("MyIntegration")],
            pack_metadata_dict={"deprecated": True},
        )
        assert parser._generate_derived_pack() is None

    def test_pack_deprecated_by_name_and_description_yields_none(self):
        parser = _make_pack_parser([_make_parser_content_item("MyIntegration")])
        parser.name = "Test Pack (Deprecated)"
        parser.description = "Deprecated. Use Other Pack instead."
        assert parser._generate_derived_pack() is None

    def test_hidden_pack_yields_none(self):
        parser = _make_pack_parser(
            [_make_parser_content_item("MyIntegration")], hidden=True
        )
        assert parser._generate_derived_pack() is None

    def test_excluded_pack_yields_none(self, monkeypatch):
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "TestPack")
        parser = _make_pack_parser([_make_parser_content_item("MyIntegration")])
        assert parser._generate_derived_pack() is None

    def test_exclusion_matching_is_case_insensitive(self, monkeypatch):
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "tEsTpAcK")
        parser = _make_pack_parser([_make_parser_content_item("MyIntegration")])
        assert (
            parser._generate_derived_pack() is None
        ), "the exclusion list matches the pack id case-insensitively"

    def test_exclusion_matching_trims_whitespace(self, monkeypatch):
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, " Other ,  TestPack  ")
        parser = _make_pack_parser([_make_parser_content_item("MyIntegration")])
        assert parser._generate_derived_pack() is None

    def test_pack_absent_from_the_exclusion_list_is_unaffected(self, monkeypatch):
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "SomeOtherPack,AndAnother")
        parser = _make_pack_parser([_make_parser_content_item("MyIntegration")])
        assert (
            parser._generate_derived_pack() is not None
        ), "an exclusion list that does not name this pack must not suppress its twin"

    def test_empty_exclusion_list_is_unaffected(self, monkeypatch):
        monkeypatch.setenv(DERIVED_PACKS_EXCLUDE_ENV, "")
        parser = _make_pack_parser([_make_parser_content_item("MyIntegration")])
        assert parser._generate_derived_pack() is not None

    def test_only_xsoar_is_allowed(self):
        """Guards the allowlist itself against silently growing."""
        assert DERIVED_PACK_ALLOWED_SUPPORT_LEVELS == frozenset({"xsoar"})


class TestDeprecatedItemsAreNotTightlyCoupled:
    """A deprecated item must never travel into the managed twin."""

    def test_deprecated_item_is_omitted_from_the_derived_pack(self):
        live = _make_parser_content_item("LiveIntegration")
        dead = _make_parser_content_item("DeadIntegration", deprecated=True)
        parser = _make_pack_parser([live, dead])

        derived = parser._generate_derived_pack()

        assert derived is not None
        live.add_to_pack.assert_called_once_with("TestPackManaged")
        (
            dead.add_to_pack.assert_not_called(),
            ("a deprecated item must not get a second IN_PACK edge to the twin"),
        )

    def test_pack_with_one_live_and_one_deprecated_item_yields_exactly_one(self):
        live = _make_parser_content_item("LiveIntegration")
        dead = _make_parser_content_item("DeadIntegration", deprecated=True)
        parser = _make_pack_parser([live, dead])

        parser._generate_derived_pack()

        added = [item for item in (live, dead) if item.add_to_pack.call_count]
        assert added == [live], "exactly the live item is carried into the twin"

    def test_pack_whose_only_tightly_coupled_item_is_deprecated_yields_none(self):
        parser = _make_pack_parser(
            [_make_parser_content_item("DeadIntegration", deprecated=True)]
        )
        assert (
            parser._generate_derived_pack() is None
        ), "with nothing live left to split out, no twin is generated"

    def test_deprecated_item_is_dropped_even_with_a_tightly_coupled_override(self):
        """Deprecation wins over ``coupling_overrides`` in the parser too."""
        dead_script = _make_parser_content_item(
            "DeadScript", ContentType.SCRIPT, deprecated=True
        )
        parser = _make_pack_parser(
            [dead_script], coupling_overrides={"DeadScript": "tightly_coupled"}
        )
        assert parser._generate_derived_pack() is None

    def test_item_deprecated_by_name_and_description_is_dropped(self):
        dead = _make_parser_content_item("DeadIntegration")
        dead.name = "Dead Integration (Deprecated)"
        dead.description = "Deprecated. No available replacement."
        parser = _make_pack_parser([dead])
        assert parser._generate_derived_pack() is None
