from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = IndicatorType


class DetailsFieldEqualsIdValidator(BaseValidator[ContentTypes]):
    error_code = "RP102"
    description = "Validate that the id and the details fields are equal."
    error_message = "id and details fields are not equal. id={0}, details={1}"
    rationale = "To align with the platform requirements."
    related_field = "id"
    expected_git_statuses = [GitStatuses.ADDED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.object_id, content_item.description
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.description != content_item.object_id
        ]
