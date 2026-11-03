from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsParamSupportedModulesNotEmptyValidator(BaseValidator[ContentTypes]):
    error_code = "IN171"
    description = (
        "Validate that if a parameter has supportedModules defined, "
        "it is not an empty list."
    )
    rationale = (
        "An empty supportedModules list on a parameter means the parameter would not be "
        "available in any module. Either remove the field entirely or specify at least one module."
    )
    error_message = (
        "Parameter '{param_name}' has an empty supportedModules list. "
        "Either remove the field or specify at least one module."
    )
    related_field = "supportedModules"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            for param in content_item.params:
                if (
                    param.supportedModules is not None
                    and len(param.supportedModules) == 0
                ):
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                param_name=param.name,
                            ),
                            content_object=content_item,
                        )
                    )
        return results
