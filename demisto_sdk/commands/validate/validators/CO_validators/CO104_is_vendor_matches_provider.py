from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsVendorMatchesProviderValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO104"
    description = (
        "Validates that a connector's metadata.vendor matches the linked "
        "integration(s)' provider field, and that all handlers agree on the "
        "same provider."
    )
    rationale = (
        "The connector's vendor is derived from the provider of the "
        "integrations it groups. If handlers reference integrations with "
        "differing providers, or if metadata.vendor does not match the "
        "shared provider, the connector's vendor is inconsistent with its "
        "underlying integrations."
    )
    error_message = (
        "Connector '{connector_id}' has a vendor/provider mismatch: " "{details}."
    )
    related_field = "metadata.vendor"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            vendor = connector.connector_metadata.vendor

            # Collect the provider of every resolved linked integration.
            providers = {
                handler.related_integration.provider
                for handler in connector.xsoar_handlers
                if handler.related_integration is not None
                and handler.related_integration.provider
            }

            details: List[str] = []

            # Flag if providers differ across handlers.
            if len(providers) > 1:
                details.append(
                    f"handlers reference integrations with differing "
                    f"providers {sorted(providers)}"
                )
            elif len(providers) == 1 and vendor not in providers:
                (provider,) = tuple(providers)
                details.append(
                    f"metadata.vendor '{vendor}' does not match integration "
                    f"provider '{provider}'"
                )

            if details:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            details="; ".join(details),
                        ),
                        content_object=connector,
                    )
                )

        return results
