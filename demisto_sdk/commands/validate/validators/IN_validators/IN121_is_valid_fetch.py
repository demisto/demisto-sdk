from __future__ import annotations

from typing import ClassVar, Iterable, List

from demisto_sdk.commands.common.constants import (
    ALERT_FETCH_REQUIRED_PARAMS,
    INCIDENT_FETCH_REQUIRED_PARAMS,
    MarketplaceVersions,
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


class IsValidFetchValidator(BaseValidator[ContentTypes]):
    error_code = "IN121"
    description = (
        "Validate that fetch integration has the required params in the right format."
    )
    rationale = (
        "Malformed or missing parameters can lead to errors or incomplete data. "
        "For more details, see https://xsoar.pan.dev/docs/integrations/fetching-incidents"
    )
    error_message = "The integration is a fetch integration and is missing/containing malformed required params:\n{0}"
    related_field = "configuration"
    missing_or_malformed_integration: ClassVar[dict] = {}

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "\n".join(
                        [
                            f"The param {key} is missing/malformed, it should be in the following format: {val}"
                            for key, val in missing_or_malformed_integration.items()
                        ]
                    )
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.is_fetch
            and (
                missing_or_malformed_integration := self.is_valid_fetch_integration(
                    content_item.name, content_item.params, content_item.marketplaces
                )
            )
        ]

    def is_valid_fetch_integration(
        self,
        integration_name: str,
        params: List[Parameter],
        marketplaces: List[MarketplaceVersions],
    ) -> dict:
        """List the missing / malformed required fetch params for the given integration

        Args:
            integration_name (str): The name of the current integration to validate.
            params (List[dict]): The list of the integration params.
            marketplaces (List[MarketplaceVersions]): The list of the current integration's supported marketplaces

        Returns:
            dict: The missing params by param_name: param_entity.
        """
        fetch_required_params = (
            INCIDENT_FETCH_REQUIRED_PARAMS
            if any(
                [
                    MarketplaceVersions.XSOAR in marketplaces,
                    MarketplaceVersions.XSOAR_SAAS in marketplaces,
                    MarketplaceVersions.XSOAR_ON_PREM in marketplaces,
                ]
            )
            else ALERT_FETCH_REQUIRED_PARAMS
        )
        current_integration = {}
        for fetch_required_param in fetch_required_params:
            if not (
                param := find_param(params, fetch_required_param.get("name", ""))  # type: ignore[arg-type]
            ) or not all(
                [
                    param.display == fetch_required_param.get("display"),
                    param.type == fetch_required_param.get("type"),
                ]
            ):
                current_integration[fetch_required_param.get("name")] = (
                    fetch_required_param
                )
        self.missing_or_malformed_integration[integration_name] = current_integration
        return current_integration
