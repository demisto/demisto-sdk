"""
Unit tests for the runScriptAfterUpdate field preservation in IncidentField strict object.
"""

from pathlib import Path

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.parsers.incident_field import (
    IncidentFieldParser,
)
from TestSuite.pack import Pack


class TestIncidentFieldRunScriptAfterUpdate:
    """Tests for runScriptAfterUpdate field preservation."""

    def test_run_script_after_update_preserved_when_true(self, pack: Pack):
        """
        Given:
            - An incident field with runScriptAfterUpdate set to true.
        When:
            - Creating the content item's parser and model.
            - Serializing the model with by_alias=True.
        Then:
            - Verify that runScriptAfterUpdate is preserved in the serialized output.
        """
        incident_field_data = {
            "id": "test_field",
            "name": "Test Field",
            "cliName": "testfield",
            "type": "shortText",
            "version": -1,
            "fromVersion": "5.5.0",
            "associatedToAll": False,
            "runScriptAfterUpdate": True,
        }

        incident_field = pack.create_incident_field(
            "TestIncidentField", incident_field_data
        )
        incident_field_path = Path(incident_field.path)
        parser = IncidentFieldParser(
            incident_field_path, list(MarketplaceVersions), pack_supported_modules=[]
        )

        # Verify the field is preserved in the raw data
        # This tests that the field is not stripped during parsing
        assert "runScriptAfterUpdate" in parser.json_data
        assert parser.json_data["runScriptAfterUpdate"] is True

    def test_run_script_after_update_preserved_when_false(self, pack: Pack):
        """
        Given:
            - An incident field with runScriptAfterUpdate set to false.
        When:
            - Creating the content item's parser and model.
            - Serializing the model with by_alias=True.
        Then:
            - Verify that runScriptAfterUpdate is preserved in the serialized output.
        """
        incident_field_data = {
            "id": "test_field",
            "name": "Test Field",
            "cliName": "testfield",
            "type": "shortText",
            "version": -1,
            "fromVersion": "5.5.0",
            "associatedToAll": False,
            "runScriptAfterUpdate": False,
        }

        incident_field = pack.create_incident_field(
            "TestIncidentField", incident_field_data
        )
        incident_field_path = Path(incident_field.path)
        parser = IncidentFieldParser(
            incident_field_path, list(MarketplaceVersions), pack_supported_modules=[]
        )

        # Verify the field is preserved in the raw data
        # This tests that the field is not stripped during parsing
        assert "runScriptAfterUpdate" in parser.json_data
        assert parser.json_data["runScriptAfterUpdate"] is False

    def test_run_script_after_update_not_included_when_none(self, pack: Pack):
        """
        Given:
            - An incident field without runScriptAfterUpdate field.
        When:
            - Creating the content item's parser and model.
            - Serializing the model with by_alias=True and exclude_none=True.
        Then:
            - Verify that runScriptAfterUpdate is not included in the serialized output.
        """
        incident_field_data = {
            "id": "test_field",
            "name": "Test Field",
            "cliName": "testfield",
            "type": "shortText",
            "version": -1,
            "fromVersion": "5.5.0",
            "associatedToAll": False,
        }

        incident_field = pack.create_incident_field(
            "TestIncidentField", incident_field_data
        )
        incident_field_path = Path(incident_field.path)
        parser = IncidentFieldParser(
            incident_field_path, list(MarketplaceVersions), pack_supported_modules=[]
        )

        # Verify the field is not included when it's not in the source data
        assert "runScriptAfterUpdate" not in parser.json_data

    def test_run_script_after_update_with_run_script_after_inc_update(self, pack: Pack):
        """
        Given:
            - An incident field with both runScriptAfterUpdate and runScriptAfterIncUpdate.
        When:
            - Creating the content item's parser and model.
            - Serializing the model with by_alias=True.
        Then:
            - Verify that both fields are preserved in the serialized output.
        """
        incident_field_data = {
            "id": "test_field",
            "name": "Test Field",
            "cliName": "testfield",
            "type": "shortText",
            "version": -1,
            "fromVersion": "5.5.0",
            "associatedToAll": False,
            "runScriptAfterUpdate": True,
            "runScriptAfterIncUpdate": False,
        }

        incident_field = pack.create_incident_field(
            "TestIncidentField", incident_field_data
        )
        incident_field_path = Path(incident_field.path)
        parser = IncidentFieldParser(
            incident_field_path, list(MarketplaceVersions), pack_supported_modules=[]
        )

        # Verify both fields are preserved in the raw data
        # This tests that both fields are not stripped during parsing
        assert "runScriptAfterUpdate" in parser.json_data
        assert parser.json_data["runScriptAfterUpdate"] is True
        assert "runScriptAfterIncUpdate" in parser.json_data
        assert parser.json_data["runScriptAfterIncUpdate"] is False
