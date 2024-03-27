from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.common.hook_validations.xdrc_templates import (
    XDRCTemplatesValidator,
)
from demisto_sdk.commands.content_graph.objects.xdrc_template import XDRCTemplate
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = XDRCTemplate


class XdrcTemplatesFilesNamingValidator(BaseValidator[ContentTypes]):
    error_code = "XT100"
    description = "Check if the files in the XDRC templates directory have a valid name"
    rationale = "So files could abide to a specific naming convention"
    error_message = "Files in the xdrc templates directory must be titled exactly as the pack, e.g. `myPack.yml`"
    related_field = ""
    is_auto_fixable = False
    expected_git_statuses = [
        GitStatuses.MODIFIED,
        GitStatuses.ADDED,
        GitStatuses.RENAMED,
    ]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (self.template_file_not_valid(content_item=content_item))
        ]

    def template_file_not_valid(self, content_item: ContentTypes):
        structure_validator = StructureValidator(
            str(content_item.path),
        )
        xdrc_templates_validator = XDRCTemplatesValidator(
            structure_validator,
            ignored_errors=None,
            json_file_path=content_item.json,
        )
        return not xdrc_templates_validator.validate_xsiam_content_item_title(
            xdrc_templates_validator.file_path
        )
