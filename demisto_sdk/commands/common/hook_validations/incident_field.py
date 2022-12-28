"""
This module is designed to validate the correctness of incident field entities in content.
"""

from typing import Set

from demisto_sdk.commands.common.hook_validations.field_base_validator import (
    FieldBaseValidator,
)


class IncidentFieldValidator(FieldBaseValidator):
    """IncidentFieldValidator is designed to validate the correctness of the file structure we enter to content repo.
    And also try to catch possible Backward compatibility breaks due to the performed changes.
    """

    FIELD_TYPES = {
        "shortText",
        "longText",
        "boolean",
        "singleSelect",
        "multiSelect",
        "date",
        "user",
        "role",
        "number",
        "attachments",
        "tagsSelect",
        "internal",
        "url",
        "markdown",
        "grid",
        "timer",
        "html",
    }
    INCIDENT_PROHIBITED_CLI_NAMES = {
        "id",
        "shardid",
        "modified",
        "autime",
        "account",
        "type",
        "rawtype",
        "phase",
        "rawphase",
        "name",
        "rawname",
        "status",
        "reason",
        "created",
        "parent",
        "occurred",
        "duedate",
        "reminder",
        "closed",
        "sla",
        "level",
        "investigationid",
        "details",
        "openduration",
        "droppedcount",
        "linkedcount",
        "closinguserId",
        "activatinguserId",
        "owner",
        "roles",
        "previousroles",
        "hasrole",
        "dbotcreatedBy",
        "activated",
        "closereason",
        "rawClosereason",
        "playbookid",
        "isplayground",
        "category",
        "rawcategory",
        "runstatus",
        "rawjson",
        "sourcebrand",
        "sourceinstance",
        "Lastopen",
        "canvases",
        "notifytime",
        "todotaskids",
        "scheduled",
        "labels",
    }
    EVIDENCE_PROHIBITED_CLI_NAMES = {
        "id",
        "shardid",
        "modified",
        "incidentid",
        "entryid",
        "description",
        "tags",
        "tagsraw",
        "occurred",
        "markeddate",
        "fetched",
        "taskid",
        "markedby",
        "roles",
        "previousroles",
        "hasrole",
        "dbotcreatedBy",
    }
    EVIDENCE_GROUP_ID = 1

    def __init__(
        self,
        structure_validator,
        ignored_errors=False,
        print_as_warnings=False,
        json_file_path=None,
        **kwargs
    ):
        prohibited_cli_names: Set[str] = (
            self.EVIDENCE_PROHIBITED_CLI_NAMES
            if structure_validator.current_file.get("group") == self.EVIDENCE_GROUP_ID
            else self.INCIDENT_PROHIBITED_CLI_NAMES
        )
        super().__init__(
            structure_validator,
            self.FIELD_TYPES,
            prohibited_cli_names,
            ignored_errors,
            print_as_warnings,
            json_file_path=json_file_path,
            **kwargs
        )
