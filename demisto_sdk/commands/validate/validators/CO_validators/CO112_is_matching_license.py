from __future__ import annotations

from typing import Iterable, List, Set

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsMatchingLicenseValidator(BaseValidator[ContentTypes]):
    error_code = "CO112"
    description = (
        "Validates that each XSOAR handler's capabilities license union "
        "contains the matched integration's supportedModules."
    )
    rationale = (
        "Each XSOAR handler serves a set of capabilities, each with a "
        "required_license. The handler's matched integration has supportedModules. "
        "The union of all the handler's capability licenses must be a superset "
        "of the integration's supportedModules to ensure proper license coverage."
    )
    error_message = (
        "Connector '{connector_id}', handler '{handler_id}': the integration "
        "'{integration_id}' has supportedModules {integration_modules} that are "
        "not covered by the handler's capabilities license union "
        "{handler_licenses}. Missing modules: {missing_modules}"
    )
    related_field = "config.required_license"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Check per-handler that the capability license union covers supportedModules.

        For each XSOAR handler with a matched integration (handler.related_integration):
        1. Collect the handler's capability IDs
        2. For each capability ID, find the matching CapabilityData
        3. Union all required_license from capabilities and sub-capabilities
        4. Check that handler.related_integration.supportedModules is a subset
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.xsoar_handlers:
                if handler.related_integration is None:
                    # No matched integration -- CO100 handles this
                    continue

                integration = handler.related_integration
                integration_modules: Set[str] = set(integration.supportedModules or [])
                if not integration_modules:
                    continue

                # Collect the union of all required_license from this handler's capabilities
                handler_licenses: Set[str] = set()
                for cap in handler.capabilities:
                    cap_data = connector.capability_by_id.get(cap.id)
                    if not cap_data:
                        continue
                    if cap_data.config and cap_data.config.required_license:
                        handler_licenses.update(cap_data.config.required_license)
                    for sub_cap in cap_data.sub_capabilities:
                        if sub_cap.required_license:
                            handler_licenses.update(sub_cap.required_license)

                if not handler_licenses:
                    continue

                if missing_modules := integration_modules - handler_licenses:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                connector_id=connector.object_id,
                                handler_id=handler.id,
                                integration_id=integration.object_id,
                                integration_modules=sorted(integration_modules),
                                handler_licenses=sorted(handler_licenses),
                                missing_modules=sorted(missing_modules),
                            ),
                            content_object=connector,
                        )
                    )

        return results
