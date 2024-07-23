from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.case_field import CaseField
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[CaseField, IncidentField]

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


class IsCliNameReservedWordValidator(BaseValidator[ContentTypes]):
    error_code = "IF106"
    description = "Checks if `cliName` field is not a reserved word."
    rationale = "The cliName values of the incident field are limited by the platform."
    error_message = "`cliName` field can not be `{cli_name}` as it's a builtin key."
    related_field = "cliName"

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(cli_name=content_item.cli_name),
                content_object=content_item,
            )
            for content_item in content_items
            if (content_item.cli_name in INCIDENT_PROHIBITED_CLI_NAMES)
        ]
