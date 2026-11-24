import pytest
from pydantic import ValidationError

from demisto_sdk.commands.content_graph.strict_objects.release_notes_config import (
    StrictReleaseNotesConfig,
)


class TestStrictReleaseNotesConfig:
    """Coverage for ReleaseNotes/x_x_x.json after the removal of ``forceUpdate`` (CIAC-18913 / CIAC-18915)."""

    def test_valid_config(self):
        """A config without ``forceUpdate`` parses successfully."""
        StrictReleaseNotesConfig.parse_obj(
            {"breakingChanges": True, "breakingChangesNotes": "BC"}
        )

    @pytest.mark.parametrize(
        "config",
        [
            # Unknown top-level field.
            {"breakingChanges": True, "unknownField": "value"},
            # forceUpdate is no longer supported.
            {
                "breakingChanges": True,
                "forceUpdate": {"breakingChangesNotesTightly": "Tightly BC note."},
            },
        ],
    )
    def test_invalid_configs(self, config: dict):
        """An unknown field, including the removed ``forceUpdate``, raises ValidationError."""
        with pytest.raises(ValidationError):
            StrictReleaseNotesConfig.parse_obj(config)
