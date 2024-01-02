from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.tools import get_current_usecases
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack


class IsValidUseCasesValidator(BaseValidator[ContentTypes]):
    error_code = "PA119"
    description = "Validate that the metadata's usecases field include valid usecases."
    error_message = "The pack metadata contains non approved usecases: {0}.\nThe list of approved use cases can be found in https://xsoar.pan.dev/docs/documentation/pack-docs#pack-keywords-tags-use-cases--categories"
    fix_message = "Removed the following use cases: {0}"
    related_field = "useCases"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        non_approved_usecases = set()
        current_usecases = get_current_usecases()
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(non_approved_usecases)),
                content_object=content_item,
            )
            for content_item in content_items
            if (non_approved_usecases := set(content_item.use_cases) - set(current_usecases))  # type: ignore
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        non_approved_usecases = set(content_item.use_cases) - set(get_current_usecases())  # type: ignore
        use_cases = content_item.use_cases
        for non_approved_usecase in non_approved_usecases:
            use_cases.remove(non_approved_usecase)  # type: ignore
        content_item.use_cases = use_cases
        return FixResult(
            validator=self,
            message=self.fix_message.format(", ".join(non_approved_usecases)),
            content_object=content_item,
        )
