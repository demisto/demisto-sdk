from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ALLOWED_CERTIFICATION_VALUES
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsValidCertificateValidator(BaseValidator[ContentTypes]):
    error_code = "PA118"
    description = "Validate that the metadata's certification field is valid."
    rationale = (
        "See the list of allowed `certification` in the platform: "
        "https://xsoar.pan.dev/docs/packs/packs-format#pack_metadatajson."
    )
    error_message = (
        "The certification field ({0}) is invalid. It can be one of the following: {1}."
    )
    related_field = "certification"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.certification, ", ".join(ALLOWED_CERTIFICATION_VALUES)
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.certification
            and content_item.certification not in ALLOWED_CERTIFICATION_VALUES
        ]
