from __future__ import annotations

from typing import ClassVar, Iterable, List

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
    rationale = (
        "See the list of allowed `useCases` in the platform: "
        "https://xsoar.pan.dev/docs/documentation/pack-docs#pack-keywords-tags-use-cases--categories"
    )
    error_message = "The pack metadata contains non approved usecases: {0}.\nThe list of approved use cases can be found in https://xsoar.pan.dev/docs/documentation/pack-docs#pack-keywords-tags-use-cases--categories"
    fix_message = "Removed the following use cases: {0}."
    related_field = "useCases"
    is_auto_fixable = True
    non_approved_usecases_dict: ClassVar[dict] = {}

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        non_approved_usecases = set()
        approved_usecases = get_current_usecases()
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(non_approved_usecases)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                non_approved_usecases := self.get_non_approved_usecases(
                    approved_usecases, content_item
                )
            )
        ]

    def get_non_approved_usecases(
        self, approved_usecases: List[str], content_item: ContentTypes
    ) -> set:
        """Extract the set of non approved usecases from the metadata's useCases field.

        Args:
            approved_usecases (List[str]): The list of approved useCases.
            content_item (ContentTypes): the pack_metadata object.

        Returns:
            set: the set of non approved usecases
        """
        non_approved_usecases = set()
        if non_approved_usecases := set(
            content_item.pack_metadata_dict.get("useCases", [])  # type: ignore[union-attr]
        ) - set(approved_usecases):
            self.non_approved_usecases_dict[content_item.name] = non_approved_usecases
        return non_approved_usecases

    def fix(self, content_item: ContentTypes) -> FixResult:
        non_approved_usecases = self.non_approved_usecases_dict[content_item.name]
        use_cases = content_item.use_cases
        for non_approved_usecase in non_approved_usecases:
            use_cases.remove(non_approved_usecase)
        content_item.use_cases = use_cases
        return FixResult(
            validator=self,
            message=self.fix_message.format(", ".join(non_approved_usecases)),
            content_object=content_item,
        )
