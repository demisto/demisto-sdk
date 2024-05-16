from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Dashboard

FIELDS_TO_INCLUDE = ["fromDate", "toDate", "fromDateLicense"]


class IsDashboardContainNecessaryFieldsValidator(BaseValidator[ContentTypes]):
    expected_git_statuses = [GitStatuses.ADDED]
    error_code = "DA101"
    description = "Validate that the dashboard includes all the necessary fields."
    rationale = "The Dashboard should contains the required 'fromDate', 'toDate', 'fromDateLicense' fields."
    dashboard_error_message = (
        "The '{0}' fields are missing from {1} and need to be added."
    )
    widget_error_message = "The '{0}' fields are missing from {1} Widget listed under {2} and need to be added."
    related_field = "layout"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        results = []
        error_messages = []
        for content_item in content_items:
            dashboard_missing_fields = self.dashboard_missing_necessary_fields(
                content_item.data_dict
            )
            widget_missing_fields = self.widget_missing_necessary_fields(content_item)

            if dashboard_missing_fields:
                error_messages.append(
                    self.dashboard_error_message.format(
                        ", ".join(dashboard_missing_fields), content_item.name
                    )
                )
            if widget_missing_fields:
                for widget in widget_missing_fields:
                    error_messages.append(
                        self.widget_error_message.format(
                            ", ".join(widget_missing_fields[widget]),
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

    def dashboard_missing_necessary_fields(self, dashboard):
        return [field for field in FIELDS_TO_INCLUDE if dashboard.get(field) is None]

    def widget_missing_necessary_fields(self, dashboard: ContentTypes):
        widgets = self.get_widgets_from_dashboard(dashboard)
        missing_fields = dict()
        for widget in widgets:
            fields = [field for field in FIELDS_TO_INCLUDE if widget.get(field) is None]
            if fields:
                missing_fields[widget.get("id")] = fields
        return missing_fields

    @staticmethod
    def get_widgets_from_dashboard(dashboard: ContentTypes) -> list:
        return [item.get("widget") for item in dashboard.layout]
