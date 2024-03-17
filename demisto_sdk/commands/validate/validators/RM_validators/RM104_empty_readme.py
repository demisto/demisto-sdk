from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    PARTNER_SUPPORT,
    XSOAR_SUPPORT,
)
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class EmptyReadmeValidator(BaseValidator[ContentTypes]):
    error_code = "RM104"
    description = (
        "Validate that the pack contains a full README.md file with pack information. "
    )
    error_message = """Pack {0} written by a partner or pack containing playbooks must have a full README.md file with pack information. Please refer to https://xsoar.pan.dev/docs/documentation/pack-docs#pack-readme for more information"""
    related_field = "readme"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.README]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.name),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                # if the pack is partner/xsoar supported or contains playbooks, it must have a full README.md file
                (
                    content_item.support in (PARTNER_SUPPORT, XSOAR_SUPPORT)
                    or content_item.content_items.playbook
                )
                and not content_item.readme.file_content
            )
        ]
