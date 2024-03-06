from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import XSOAR_SUPPORT, ParameterType
from demisto_sdk.commands.content_graph.objects.integration import (
    Integration,
    Parameter,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsAPITokenInCredentialTypeValidator(BaseValidator[ContentTypes]):
    error_code = "IN145"
    description = "Validate that xsoar supported integrations don't have a non-hidden type 4 params."
    error_message = "In order to allow fetching the following params: {0} from an external vault, the type of the parameters should be changed from 'Encrypted' (type 4), to 'Credentials' (type 9)'.\nFor more details, check the convention for credentials - https://xsoar.pan.dev/docs/integrations/code-conventions#credentials"
    related_field = "configuration"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_params)),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.support_level == XSOAR_SUPPORT
            and (invalid_params := self.get_invalid_params(content_item.params))
        ]

    def get_invalid_params(self, params: List[Parameter]) -> List[str]:
        return [
            param.name
            for param in params
            if param.type == ParameterType.ENCRYPTED.value and not param.hidden
        ]
