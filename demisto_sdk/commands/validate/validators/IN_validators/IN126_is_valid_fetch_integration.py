from __future__ import annotations

from typing import ClassVar, Iterable, List

from demisto_sdk.commands.common.constants import (
    FIRST_FETCH,
    FIRST_FETCH_PARAM,
    MAX_FETCH,
    MAX_FETCH_PARAM,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.tools import find_param
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsValidFetchIntegrationValidator(BaseValidator[ContentTypes]):
    error_code = "IN126"
    description = "Validate that a fetch integration is not missing the first_fetch & max_fetch params."
    error_message = (
        "The integration is a fetch integration and missing the following params: {0}."
    )
    fix_message = "Add the following params to the integration: {0}."
    related_field = "configurations."
    is_auto_fixable = True
    missing_fetch_params: ClassVar[dict] = {}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
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
            and not (
                missing_params := self.is_Valid_fetch_integration(
                    content_item.name, content_item.params
                )
            )
        ]

    def is_Valid_fetch_integration(
        self, integration_name: str, params: List[dict]
    ) -> dict:
        """_summary_

        Args:
            integration_name (str): The name of the current integration to validate.
            params (List[dict]): The list of the integration params.

        Returns:
            dict: The missing param by param_name: param_entity.
        """
        if not find_param(params, MAX_FETCH):
            self.missing_fetch_params[integration_name] = {MAX_FETCH: MAX_FETCH_PARAM}
        if not find_param(params, FIRST_FETCH):
            self.missing_fetch_params[integration_name] = self.missing_fetch_params.get(
                integration_name, {}
            )
            self.missing_fetch_params[integration_name].update(
                {FIRST_FETCH: FIRST_FETCH_PARAM}
            )
        return self.missing_fetch_params.get(integration_name, {})

    def fix(self, content_item: ContentTypes) -> FixResult:
        for missing_param in self.missing_fetch_params.values():
            content_item.params.append(missing_param)
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                ", ".join(list(self.missing_fetch_params.keys()))
            ),
            content_object=content_item,
        )
