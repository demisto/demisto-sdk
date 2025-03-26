from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

FIELDS_TO_INCLUDE = ["hours", "days", "weeks", "hoursR", "daysR", "weeksR"]
ContentTypes = IncidentType


class IncidentTypeValidAutoExtractFieldsValidator(BaseValidator[ContentTypes]):
    error_code = "IT102"
    rationale = "extractSettings field is supposed to be in the correct format."
    description = "Check if extractSettings field is valid."
    error_message = (
        "The following incident fields are not formatted correctly under"
        "`fieldCliNameToExtractSettings`: {0}\n"
        "Please format them in one of the following ways:\n"
        "1. To extract all indicators from the field: \n"
        'isExtractingAllIndicatorTypes: true, extractAsIsIndicatorTypeId: "", '
        "extractIndicatorTypesIDs: []\n"
        "2. To extract the incident field to a specific indicator without using regex: \n"
        'isExtractingAllIndicatorTypes: false, extractAsIsIndicatorTypeId: "INDICATOR_TYPE", '
        "extractIndicatorTypesIDs: []\n"
        "3. To extract indicators from the field using regex: \n"
        'isExtractingAllIndicatorTypes: false, extractAsIsIndicatorTypeId: "", '
        'extractIndicatorTypesIDs: ["INDICATOR_TYPE1", "INDICATOR_TYPE2"]'
    )
    related_field = "extractSettings"

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_incident_fields)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                invalid_incident_fields := self.invalid_auto_extract_fields(
                    content_item
                )
            )
        ]

    @staticmethod
    def invalid_auto_extract_fields(incident_type: ContentTypes):
        invalid_incident_fields: list = []
        auto_extract_data = incident_type.extract_settings

        if not auto_extract_data:
            return invalid_incident_fields

        auto_extract_fields = auto_extract_data.get("fieldCliNameToExtractSettings")

        if auto_extract_fields:
            for incident_field, extracted_settings in auto_extract_fields.items():
                extracting_all = extracted_settings.get("isExtractingAllIndicatorTypes")
                extract_as_is = extracted_settings.get("extractAsIsIndicatorTypeId")
                extracted_indicator_types = extracted_settings.get(
                    "extractIndicatorTypesIDs"
                )

                # General format check.
                if (
                    not isinstance(extracting_all, bool)
                    or not isinstance(extract_as_is, str)
                    or not isinstance(extracted_indicator_types, list)
                ):
                    invalid_incident_fields.append(incident_field)

                # If trying to extract without regex make sure extract all is set to
                # False and the extracted indicators list is empty
                elif extract_as_is != "":
                    if extracting_all is True or len(extracted_indicator_types) > 0:
                        invalid_incident_fields.append(incident_field)

                # If trying to extract with regex make sure extract all is set to
                # False and the extract_as_is should be set to an empty string
                elif len(extracted_indicator_types) > 0:
                    if extracting_all is True or extract_as_is != "":
                        invalid_incident_fields.append(incident_field)

        return invalid_incident_fields
