
from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.hook_validations.xdrc_templates import XDRCTemplatesValidator
from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import XSIAMDashboard
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = XSIAMDashboard


class XdrcTemplatesFilesNamingValidator(BaseValidator[ContentTypes]):
    error_code = "XT100"
    description = "Check if the files in the xdrc templates directory have a valid name"
    rationale = "No idea"
    error_message = "Files in the xdrc templates directory must be titled exactly as the pack, e.g. `myPack.yml`."
    related_field = ""
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.ADDED]

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                # Add your validation right here
            )
        ]
    
    def check(self, content_item: ContentTypes):
        xdrc_templates_validator = XDRCTemplatesValidator(
            None,
            ignored_errors=None,
            json_file_path=content_item.json,
        )

    
