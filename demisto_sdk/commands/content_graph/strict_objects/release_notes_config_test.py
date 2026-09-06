import pytest
from pydantic import ValidationError

from demisto_sdk.commands.content_graph.strict_objects.release_notes_config import (
    StrictReleaseNotesConfig,
)


class TestStrictReleaseNotesConfigForceUpdate:
    """
    Coverage for the optional `forceUpdate` object added to the per-version breaking-changes config
    (ReleaseNotes/x_x_x.json) for the ConnectUS (Managed Content) flow. See CIAC-17085 / CIAC-17086.
    """

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
            # forceUpdate with empty-string notes (as authored in content).
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
        """
        Given: A release-notes-config dict with a valid (optional) forceUpdate object.
        When: Parsing it with StrictReleaseNotesConfig.
        Then: Parsing succeeds.
        """
        StrictReleaseNotesConfig.parse_obj(config)

    @pytest.mark.parametrize(
        "config",
        [
            # Unknown top-level field.
            {"breakingChanges": True, "unknownField": "value"},
            # Unknown field nested inside forceUpdate.
            {"breakingChanges": True, "forceUpdate": {"unknownField": "value"}},
            # breakingChangesNotesTightly is now a plain string - an object is rejected.
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
        """
        Given: A release-notes-config dict with an invalid forceUpdate (unknown field, or a non-string
            breakingChangesNotesTightly).
        When: Parsing it with StrictReleaseNotesConfig.
        Then: A ValidationError is raised.
        """
        with pytest.raises(ValidationError):
            StrictReleaseNotesConfig.parse_obj(config)
