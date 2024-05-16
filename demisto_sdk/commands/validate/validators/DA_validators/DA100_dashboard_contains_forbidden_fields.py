from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
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
    expected_git_statuses = [GitStatuses.ADDED]
    error_code = "DA100"
    description = "Validate that the dashboard excludes all the unnecessary fields."
    rationale = "The Dashboard should contains only the required fields."
    dashboard_error_message = "The '{0}' fields need to be removed from {1}."
    widgets_error_message = (
        "The '{0}' fields need to be removed from {1} Widget listed under {2}."
    )
    related_field = "layout"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        results = []
        error_messages = []
        for content_item in content_items:
            invalid_dashboard_fields = self.dashboard_contains_forbidden_fields(
                content_item.data_dict
            )
            invalid_widgets_fields = self.widgets_contain_forbidden_fields(content_item)

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

    @staticmethod
    def dashboard_contains_forbidden_fields(dashboard) -> List[str]:

        invalid_fields = [
            field for field in FIELDS_TO_EXCLUDE if dashboard.get(field) is not None
        ]
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
    def get_widgets_from_dashboard(dashboard: ContentTypes) -> list:
        return [item.get("widget") for item in dashboard.layout]
