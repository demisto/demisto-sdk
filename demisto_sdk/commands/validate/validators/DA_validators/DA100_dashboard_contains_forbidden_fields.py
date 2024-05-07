from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List

from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Dashboard

FIELDS_TO_EXCLUDE = [
    "system",
    "isCommon",
    "shared",
    "owner",
    "sortValues",
    "vcShouldIgnore",
    "commitMessage",
    "shouldCommit",
]


class IsDashboardContainForbiddenFieldsValidator(BaseValidator[ContentTypes]):
    error_code = "DA100"
    description = "Validate that the dashboard excludes all the unnecessary fields."
    rationale = "The Dashboard should contains only the required fields."
    dashboard_error_message = "the '{0}' fields need to be removed from {1}."
    widgets_error_message = (
        "the '{0}' fields need to be removed from {1} Widget in {2}."
    )
    related_field = ""
    # is_auto_fixable = True
    # fix_message = "removed the following fields {0}."
    invalid_fields: ClassVar[Dict[str, list]] = {}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        results = []
        error_messages = []
        for content_item in content_items:
            invalid_dashboard_fields = self.dashboard_contains_forbidden_fields(
                content_item.name, content_item.data
            )
            invalid_widgets_fields = self.widgets_contain_forbidden_fields(
                content_item.data
            )

            if invalid_dashboard_fields:
                error_messages.append(
                    self.dashboard_error_message.format(
                        ", ".join(invalid_dashboard_fields), content_item.name
                    )
                )

            if invalid_widgets_fields:
                for widget in invalid_widgets_fields:
                    error_messages.append(
                        self.widgets_error_message.format(
                            ", ".join(invalid_widgets_fields[widget]),
                            widget,
                            content_item.name,
                        )
                    )

            if error_messages:
                results.append(
                    ValidationResult(
                        validator=self,
                        message="\n".join(error_messages),
                        content_object=content_item,
                    )
                )
        return results

    def dashboard_contains_forbidden_fields(self, name, dashboard) -> List[str]:

        invalid_fields = [
            field for field in FIELDS_TO_EXCLUDE if dashboard.get(field) is not None
        ]
        self.invalid_fields[name] = invalid_fields
        return invalid_fields

    def widgets_contain_forbidden_fields(self, dashboard) -> dict:
        widgets = self.get_widgets_from_dashboard(dashboard)
        invalid_fields = dict()
        for widget in widgets:
            fields = [
                field for field in FIELDS_TO_EXCLUDE if widget.get(field) is not None
            ]
            if fields:
                invalid_fields[widget.get("id")] = fields
        return invalid_fields

    @staticmethod
    def get_widgets_from_dashboard(dashboard) -> list:
        layout_of_dashboard: list = dashboard.get("layout", [])
        widgets = []
        if layout_of_dashboard:
            widgets = [item.get("widget") for item in layout_of_dashboard]
        return widgets
