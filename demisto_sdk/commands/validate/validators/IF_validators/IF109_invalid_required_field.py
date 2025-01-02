from __future__ import annotations

from typing import Iterable, List, Union, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[IncidentField, IndicatorField, IncidentType, IndicatorType]


class IsValidRequiredFieldValidator(BaseValidator[ContentTypes]):
    error_code = "IF109"
    description = "Checks if the incident field required field is valid."
    rationale = "In case an incident field is required, newly added associated incident types should be new."
    # error_message = "{0}"
    related_field = "required"
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.ADDED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:

        types_items = []
        fields_items = []
        for item in content_items:
            if (
                isinstance(item, IncidentType) or isinstance(item, IndicatorType)
            ) and item.git_status == GitStatuses.ADDED:
                types_items.append(item.object_id)
            elif isinstance(item, IncidentField) or isinstance(item, IndicatorField):
                fields_items.append(item)

        return [
            ValidationResult(
                validator=self,
                message=error_res,
                content_object=content_item,
            )
            for content_item in fields_items
            if (error_res := self.is_invalid_required_field(content_item, types_items))
        ]
    @staticmethod
    def is_invalid_required_field(content_item, added_types):

        # Required fields should not be associated to all
        if content_item.required and content_item.associated_to_all:
            return "Required field should not be associated to all types."

        if content_item.git_status == GitStatuses.MODIFIED:
            old_file = cast(ContentTypes, content_item.old_base_content_object)

            # Required value for an already existing field cannot be changed
            if content_item.required != old_file.required:
                return (
                    f"Required value should not be changed for an already existing"
                    f" {'Incident' if isinstance(content_item, IncidentField) else 'Indicator'} Field."
                )

            # An already existing Incident/Indicator Type cannot be added to Incident/Indicator Field with required value true
            if content_item.required and len(content_item.associated_types) > len(
                    old_file.associated_types
            ):
                new_types = list(
                    filter(
                        lambda x: x not in old_file.associated_types,
                        content_item.associated_types,
                    )
                )
                for new_type in new_types:
                    if new_type not in added_types:
                        return (
                            f"An already existing Type like {new_type} cannot be added to an "
                            f"{'Incident' if isinstance(content_item, IncidentField) else 'Indicator'} "
                            f"Field with required value equals true."
                        )

        # new field
        elif content_item.required:
            associated_types = content_item.associated_types

            # An already existing Incident/Indicator Type cannot be added to Incident/Indicator Field with required value true
            for associated_type in associated_types:
                if associated_type not in added_types:
                    return(
                        f"An already existing Type like {associated_type} cannot be added to an "
                        f"{'Incident' if isinstance(content_item, IncidentField) else 'Indicator'} "
                        f"Field with required value equals true."
                    )
        return

