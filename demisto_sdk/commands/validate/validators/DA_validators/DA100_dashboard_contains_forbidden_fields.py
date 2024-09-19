from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Dashboard

FIELDS_TO_EXCLUDE = {
    "system",
    "isCommon",
    "shared",
    "owner",
    "sortValues",
    "vcShouldIgnore",
    "commitMessage",
    "shouldCommit",
}


class IsDashboardContainForbiddenFieldsValidator(BaseValidator[ContentTypes]):
    expected_git_statuses = [GitStatuses.ADDED]
    error_code = "DA100"
    description = "Validate that the dashboard excludes all the unnecessary fields."
    rationale = "The Dashboard should contain only the required fields."
    dashboard_error_message = "The '{0}' fields need to be removed from {1}."
    widgets_error_message = (
        "The '{0}' fields need to be removed from {1} Widget listed under {2}."
    )
    fix_message = "Removed all unnecessary fields from {}: " + ", ".join(
        FIELDS_TO_EXCLUDE
    )
    related_field = "layout"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results = []
        for content_item in content_items:
            error_messages = []
            invalid_dashboard_fields = FIELDS_TO_EXCLUDE.intersection(
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

    def widgets_contain_forbidden_fields(self, dashboard: ContentTypes) -> dict:
        widgets = [item.get("widget", {}) for item in dashboard.layout]
        return {
            widget.get("id"): fields
            for widget in widgets
            if (fields := FIELDS_TO_EXCLUDE.intersection(widget))
        }

    def fix(self, content_item: Dashboard) -> FixResult:
        for field in FIELDS_TO_EXCLUDE:
            content_item.data_dict.pop(field, None)

        for item in content_item.layout:
            new_item = item.get("widget", {})
            for field in FIELDS_TO_EXCLUDE:
                new_item.pop(field, None)
            item["widget"] = new_item

        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.name),
            content_object=content_item,
        )
