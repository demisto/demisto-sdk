from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack
json = JSON_Handler()


class ValidVersionConfigFileValidator(BaseValidator[ContentTypes]):
    error_code = "VC100"
    description = "Verify valid json"
    rationale = "Verify the file is valid to prevent packs showing in non compatible server versions."
    error_message = "version config file is not a valid json"
    related_field = "version_config"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]
    related_file_type = [RelatedFileType.VERSION_CONFIG]

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
            if content_item.version_config.exist
            and content_item.version_config.file_content
        ]
