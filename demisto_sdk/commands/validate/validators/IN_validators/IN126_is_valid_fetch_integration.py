from __future__ import annotations

from typing import ClassVar, Iterable, List

from demisto_sdk.commands.common.constants import (
    FIRST_FETCH,
    FIRST_FETCH_PARAM,
    MAX_FETCH,
    MAX_FETCH_PARAM,
)
from demisto_sdk.commands.content_graph.objects.integration import (
    Integration,
    Parameter,
)
from demisto_sdk.commands.validate.tools import find_param
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidFetchIntegrationValidator(BaseValidator[ContentTypes]):
    error_code = "IN126"
    description = "Validate that a fetch integration is not missing the first_fetch & max_fetch params."
    rationale = (
        "'first_fetch' and 'max_fetch' parameters in fetch integrations ensure correct incident retrieval. "
        "Their absence or incorrect format can lead to errors or inconsistencies. "
        "For more details, see https://xsoar.pan.dev/docs/integrations/fetching-incidents#first-run"
    )
    error_message = (
        "The integration is a fetch integration and missing the following params: {0}."
    )
    related_field = "configurations."
    missing_fetch_params: ClassVar[dict] = {}

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    ", ".join(list(missing_params.keys()))
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.is_fetch
            and (
                missing_params := self.is_valid_fetch_integration(
                    content_item.name, content_item.params
                )
            )
        ]

    def is_valid_fetch_integration(
        self, integration_name: str, params: List[Parameter]
    ) -> dict:
        """_summary_

        Args:
            integration_name (str): The name of the current integration to validate.
            params (List[dict]): The list of the integration params.

        Returns:
            dict: The missing param by param_name: param_entity.
        """
        self.missing_fetch_params[integration_name] = {
            key: val
            for key, val in {
                MAX_FETCH: MAX_FETCH_PARAM,
                FIRST_FETCH: FIRST_FETCH_PARAM,
            }.items()
            if not find_param(params, key)
        }
        return self.missing_fetch_params.get(integration_name, {})
