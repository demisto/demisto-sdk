from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import (
    RelatedFile,
    RelatedFileType,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack


class PackFilesValidator(BaseValidator[ContentTypes]):
    error_code = "PA128"
    description = "Checks for required pack files"
    rationale = "These files are standard in the demisto/content repo."
    error_message = "Packs require a .secrets_ignore, .pack-ignore and README"
    fix_message = "Created required files, empty."
    related_field = "secrets-ignore,pack-ignore,readme"
    is_auto_fixable = True
    related_file_type = [
        RelatedFileType.README,
        RelatedFileType.PACK_IGNORE,
        RelatedFileType.SECRETS_IGNORE,
    ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if not all(
                related_file.exist for related_file in find_related_files(content_item)
            )
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        for meta_file in find_related_files(content_item):
            if not meta_file.exist:
                logger.debug(f"creating {type(meta_file)} {meta_file.file_path!s}")
                meta_file.file_path.touch()
                meta_file.exist = True

        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )


def find_related_files(content_item: ContentTypes) -> tuple[RelatedFile, ...]:
    return (
        content_item.readme,
        content_item.secrets_ignore,
        content_item.pack_ignore,
    )
