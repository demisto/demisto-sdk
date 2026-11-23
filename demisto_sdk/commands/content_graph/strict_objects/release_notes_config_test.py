import pytest
from pydantic import ValidationError

from demisto_sdk.commands.content_graph.strict_objects.release_notes_config import (
    StrictReleaseNotesConfig,
)


class TestStrictReleaseNotesConfigForceUpdate:
    """Coverage for the optional ``forceUpdate`` object in ReleaseNotes/x_x_x.json (CIAC-17085 / CIAC-17086)."""

    @pytest.mark.parametrize(
        "config",
        [
            # Backward compatible: no forceUpdate at all.
            {"breakingChanges": True, "breakingChangesNotes": "BC"},
            # forceUpdate with only the loosely note.
            {
                "breakingChanges": True,
                "forceUpdate": {"breakingChangesNotesLoosely": "Loosely BC note."},
            },
            # forceUpdate with only the tightly note (a Markdown string).
            {
                "breakingChanges": True,
                "forceUpdate": {"breakingChangesNotesTightly": "Tightly BC note."},
            },
            # forceUpdate with both notes populated.
            {
                "breakingChanges": True,
                "forceUpdate": {
                    "breakingChangesNotesLoosely": "Loosely BC note.",
                    "breakingChangesNotesTightly": "Tightly BC note.",
                },
            },
            # forceUpdate with empty-string notes.
            {
                "breakingChanges": True,
                "forceUpdate": {
                    "breakingChangesNotesLoosely": "",
                    "breakingChangesNotesTightly": "",
                },
            },
        ],
    )
    def test_valid_force_update_configs(self, config: dict):
        """A valid optional ``forceUpdate`` parses successfully."""
        StrictReleaseNotesConfig.parse_obj(config)

    @pytest.mark.parametrize(
        "config",
        [
            # Unknown top-level field.
            {"breakingChanges": True, "unknownField": "value"},
            # Unknown field nested inside forceUpdate.
            {"breakingChanges": True, "forceUpdate": {"unknownField": "value"}},
            # breakingChangesNotesTightly is a plain string - an object is rejected.
            {
                "breakingChanges": True,
                "forceUpdate": {
                    "breakingChangesNotesTightly": {
                        "message": "Short banner text.",
                        "moreInfo": "Detailed modal text.",
                    }
                },
            },
        ],
    )
    def test_invalid_force_update_configs(self, config: dict):
        """An unknown field, or a non-string ``breakingChangesNotesTightly``, raises ValidationError."""
        with pytest.raises(ValidationError):
            StrictReleaseNotesConfig.parse_obj(config)
