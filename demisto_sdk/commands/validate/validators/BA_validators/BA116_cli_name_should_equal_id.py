from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[IncidentField, IndicatorField]


class CliNameMatchIdValidator(BaseValidator[ContentTypes]):
    error_code = "BA116"
    description = (
        "validate that the CLI name and the id match for incident and indicators field"
    )
    error_message = "The cli name {0} doesn't match the {1} id {2}"
    fix_message = "Changing the cli name to be equal to id ({0})."
    related_field = "cli_name, id"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        cli_name_expected = ""
        for content_item in content_items:
            _id = content_item.id.lower().replace("_", "").replace("-", "")
            if _id.startswith("incident"):
                cli_name_expected = _id[len("incident") :]
            elif _id.startswith("indicator"):
                cli_name_expected = _id[len("indicator") :]
            if (
                cli_name_expected and content_item.cli_name != cli_name_expected
            ) and content_item.cli_name != _id:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_item.cli_name,
                            content_item.content_type,
                            content_item.id,
                        ),
                        content_object=content_item,
                    )
                )
        return results

    def fix(self, content_item: ContentTypes) -> FixResult:
        id = content_item.id.lower().replace("_", "").replace("-", "")
        if id.startswith("incident"):
            id = id[len("incident") :]
        elif id.startswith("indicator"):
            id = id[len("indicator") :]
        content_item.cli_name = id
        return FixResult(
            validator=self,
            message=self.fix_message.format(id),
            content_object=content_item,
        )
