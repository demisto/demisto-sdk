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
    error_message = "{0}"
    related_field = "required"

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        fields_items, types_items = self.sort_content_items(content_items)
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(error_res),
                content_object=content_item,
            )
            for content_item in fields_items
            if (error_res := self.is_invalid_required_field(content_item, types_items))
        ]

    @staticmethod
    def sort_content_items(content_items: Iterable[ContentTypes]):
        """
        Sort Content Items into two lists of Incident/Indicator fields and Incident/Indicator types.

        Args:
            content_items (Iterable[ContentTypes]): The content items list

        Returns:
            fields_items: items of type Incident/Indicator fields.
            types_items: items of type Incident/Indicator types.
        """
        types_items: list[str] = []
        fields_items: list[Union[IncidentField, IndicatorField]] = []
        for item in content_items:
            if (
                isinstance(item, IncidentType) or isinstance(item, IndicatorType)
            ) and item.git_status == GitStatuses.ADDED:
                types_items.append(item.object_id)
            elif isinstance(item, IncidentField) or isinstance(item, IndicatorField):
                fields_items.append(item)

        return fields_items, types_items

    @staticmethod
    def is_invalid_required_field(
        content_item: Union[IncidentField, IndicatorField], added_types: list[str]
    ):
        """
        Get from the graph the actual fields for the given aliases

        Args:
            content_item (Union[IncidentField, IndicatorField]): The incident field or indicator field to check its required field.
            added_types (list): incident or indicator types that were created/added in the same pull request.

        Returns:
            str or None: return none in case it's valid, the error message in case it's not.
        """
        # Required fields should not be associated to all
        if content_item.required and content_item.associated_to_all:
            return (
                f"A required {content_item.content_type.value}"
                f" should not be associated with all types."
            )

        if content_item.git_status == GitStatuses.MODIFIED:
            old_file = cast(
                Union[IncidentField, IndicatorField],
                content_item.old_base_content_object,
            )

            # Required value for an already existing field cannot be changed
            if content_item.required != old_file.required:
                return (
                    f"Required value should not be changed for an already existing"
                    f" {content_item.content_type.value}."
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
                invalid_new_types = []
                for new_type in new_types:
                    if new_type not in added_types:
                        invalid_new_types.append(new_type)
                if invalid_new_types:
                    return (
                        f"An already existing Type like {', '.join(invalid_new_types)} cannot be added to an "
                        f"{content_item.content_type.value} "
                        f"with required value equals true."
                    )

        # new field
        elif content_item.required:
            associated_types = content_item.associated_types
            invalid_associated_types = []
            # An already existing Incident/Indicator Type cannot be added to Incident/Indicator Field with required value true
            for associated_type in associated_types:
                if associated_type not in added_types:
                    invalid_associated_types.append(associated_type)
            if invalid_associated_types:
                return (
                    f"An already existing Types like {', '.join(invalid_associated_types)} cannot be added to an "
                    f"{content_item.content_type.value} "
                    f"with required value equals true."
                )
        return
