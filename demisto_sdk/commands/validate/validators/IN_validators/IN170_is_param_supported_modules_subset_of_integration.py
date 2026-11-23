from __future__ import annotations

from typing import Iterable, List, Set

from demisto_sdk.commands.common.constants import PlatformSupportedModules
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsParamSupportedModulesSubsetOfIntegrationValidator(BaseValidator[ContentTypes]):
    error_code = "IN170"
    description = (
        "Validate that each parameter's supportedModules is a subset "
        "of the integration's supportedModules."
    )
    rationale = (
        "A parameter cannot support modules that the integration itself does not support. "
        "The parameter's supportedModules must be a subset of the integration's supportedModules."
    )
    error_message = (
        "Parameter '{param_name}' has supportedModules {param_modules} "
        "which are not a subset of the integration's supportedModules {integration_modules}."
    )
    related_field = "supportedModules"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            integration_modules: Set[str] = (
                set(content_item.supportedModules)
                if content_item.supportedModules
                else {module.value for module in PlatformSupportedModules}
            )
            for param in content_item.params:
                if param.supportedModules is None:
                    continue
                param_modules = set(param.supportedModules)
                if not param_modules.issubset(integration_modules):
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                param_name=param.name,
                                param_modules=sorted(param_modules),
                                integration_modules=sorted(integration_modules),
                            ),
                            content_object=content_item,
                        )
                    )
        return results
