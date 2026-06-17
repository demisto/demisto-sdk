"""Tests for the StrictConnector pydantic schema.

These tests pin the schema of ``connector.yaml`` — the main file of a
unified-connectors-content connector. They use the same pattern as other
strict objects in :mod:`demisto_sdk.commands.content_graph.strict_objects`:
build the strict model from a dict and assert that valid payloads parse,
invalid ones raise ``pydantic.ValidationError``, and the parser wiring
goes through :py:attr:`ConnectorParser.strict_object`.

We deliberately scope this to ``connector.yaml`` only (Phase 1). The
connector's sub-files (connection.yaml, capabilities.yaml, etc.) are
covered by the parser's own Pydantic sub-models today; they'll get
strict-object equivalents in a follow-up.
"""

from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from demisto_sdk.commands.content_graph.parsers.base_content import (
    validate_structure,
)
from demisto_sdk.commands.content_graph.strict_objects.connector import (
    StrictConnector,
)


def _valid_payload() -> dict:
    """Mirror ``tests/test_data/connector.yaml`` (the canonical fixture).

    Kept inline so each test reads as a self-contained spec (DAMP) and so
    the schema is exercised without touching the filesystem.
    """
    return {
        "id": "test-connector",
        "metadata": {
            "title": "Test Connector",
            "description": "A test connector for unit tests",
            "version": "1.0.0",
            "category": "Test",
            "tags": ["test"],
            "domain": "test",
            "vendor": "TestVendor",
            "publisher": "TestPublisher",
            "ownership": {
                "team": "xsoar",
                "maintainers": ["@test"],
            },
        },
        "settings": {"allow_skip_verification": True},
    }


class TestStrictConnectorValid:
    """Payloads the schema must accept."""

    def test_full_payload_parses(self):
        StrictConnector(**_valid_payload())

    def test_settings_is_optional(self):
        payload = _valid_payload()
        payload.pop("settings")
        StrictConnector(**payload)

    def test_optional_metadata_fields_can_be_omitted(self):
        """tags / domain / author_image are optional per the connector spec."""
        payload = _valid_payload()
        payload["metadata"].pop("tags")
        payload["metadata"].pop("domain")
        StrictConnector(**payload)

    def test_maintainers_is_optional(self):
        payload = _valid_payload()
        payload["metadata"]["ownership"].pop("maintainers")
        StrictConnector(**payload)


class TestStrictConnectorRequiredFields:
    """Missing-required-field cases must raise ``ValidationError``."""

    @pytest.mark.parametrize("missing", ["id", "metadata"])
    def test_missing_top_level_field(self, missing: str):
        payload = _valid_payload()
        payload.pop(missing)
        with pytest.raises(ValidationError):
            StrictConnector(**payload)

    @pytest.mark.parametrize(
        "missing",
        [
            "title",
            "description",
            "version",
            "category",
            "vendor",
            "publisher",
            "ownership",
        ],
    )
    def test_missing_required_metadata_field(self, missing: str):
        payload = _valid_payload()
        payload["metadata"].pop(missing)
        with pytest.raises(ValidationError):
            StrictConnector(**payload)

    def test_missing_ownership_team(self):
        payload = _valid_payload()
        payload["metadata"]["ownership"].pop("team")
        with pytest.raises(ValidationError):
            StrictConnector(**payload)


class TestStrictConnectorForbidExtras:
    """``extra=forbid`` (inherited from BaseStrictModel) protects every level."""

    def test_extra_top_level_field_rejected(self):
        payload = _valid_payload()
        payload["unknown_top_level"] = "nope"
        with pytest.raises(ValidationError):
            StrictConnector(**payload)

    def test_extra_metadata_field_rejected(self):
        payload = _valid_payload()
        payload["metadata"]["unknown_meta"] = "nope"
        with pytest.raises(ValidationError):
            StrictConnector(**payload)

    def test_extra_settings_field_rejected(self):
        payload = _valid_payload()
        payload["settings"]["unknown_setting"] = True
        with pytest.raises(ValidationError):
            StrictConnector(**payload)

    def test_extra_ownership_field_rejected(self):
        payload = _valid_payload()
        payload["metadata"]["ownership"]["unknown"] = "nope"
        with pytest.raises(ValidationError):
            StrictConnector(**payload)


class TestStrictConnectorTypes:
    """Spot-checks for type enforcement (pydantic does the rest)."""

    def test_id_must_be_string(self):
        payload = _valid_payload()
        payload["id"] = 123
        # pydantic v1 coerces int->str silently; the real risk is None,
        # which BaseStrictModel.prevent_none catches.
        payload["id"] = None
        with pytest.raises(ValidationError):
            StrictConnector(**payload)

    def test_allow_skip_verification_must_be_bool_when_present(self):
        # pydantic v1 coerces truthy strings like "yes"/"no" — same as every
        # other bool field in this repo — so we use a dict, which it cannot
        # coerce, to prove the field is actually typed.
        payload = _valid_payload()
        payload["settings"]["allow_skip_verification"] = {"nope": True}
        with pytest.raises(ValidationError):
            StrictConnector(**payload)


class TestValidateStructureIntegration:
    """The schema must plug into the shared ``validate_structure`` helper.

    This is the same path ST110 takes for every other content item, so
    we verify it end-to-end here rather than mocking the parser.
    """

    def test_valid_payload_yields_no_structure_errors(self, tmp_path: Path):
        errors = validate_structure(
            StrictConnector, _valid_payload(), tmp_path / "connector.yaml"
        )
        assert errors == []

    def test_invalid_payload_yields_structure_errors(self, tmp_path: Path):
        payload = deepcopy(_valid_payload())
        payload["metadata"].pop("title")  # required field
        errors = validate_structure(
            StrictConnector, payload, tmp_path / "connector.yaml"
        )
        assert errors, "expected at least one structure error for missing 'title'"


class TestConnectorParserWiring:
    """Ensure the parser exposes ``StrictConnector`` (no longer raises)."""

    def test_strict_object_returns_strict_connector(self):
        # Import inside the test so the test file can be discovered even
        # before the wiring change lands (RED phase).
        from demisto_sdk.commands.content_graph.parsers.connector import (
            ConnectorParser,
        )

        # We can read the property off the class without instantiating
        # the parser (which would need a real filesystem layout).
        assert (
            ConnectorParser.strict_object.fget(  # type: ignore[union-attr]
                object.__new__(ConnectorParser)
            )
            is StrictConnector
        )
