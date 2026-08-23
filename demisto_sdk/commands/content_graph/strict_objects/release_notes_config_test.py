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
            # forceUpdate with the tightly note as an object.
            {
                "breakingChanges": True,
                "forceUpdate": {
                    "breakingChangesNotesTightly": {
                        "message": "Short banner text.",
                        "more_info": "Detailed modal text.",
                    }
                },
            },
            # forceUpdate with the tightly note as a plain string.
            {
                "breakingChanges": True,
                "forceUpdate": {"breakingChangesNotesTightly": "Tightly BC note."},
            },
            # forceUpdate with both notes populated.
            {
                "breakingChanges": True,
                "forceUpdate": {
                    "breakingChangesNotesLoosely": "Loosely BC note.",
                    "breakingChangesNotesTightly": {
                        "message": "Short banner text.",
                        "more_info": "Detailed modal text.",
                    },
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
            # Unknown field nested inside breakingChangesNotesTightly.
            {
                "breakingChanges": True,
                "forceUpdate": {
                    "breakingChangesNotesTightly": {"unknownField": "value"}
                },
            },
        ],
    )
    def test_invalid_force_update_configs_reject_extra_fields(self, config: dict):
        """
        Given: A release-notes-config dict with an unknown field (top-level or nested).
        When: Parsing it with StrictReleaseNotesConfig.
        Then: A ValidationError is raised (Extra.forbid).
        """
        with pytest.raises(ValidationError):
            StrictReleaseNotesConfig.parse_obj(config)
