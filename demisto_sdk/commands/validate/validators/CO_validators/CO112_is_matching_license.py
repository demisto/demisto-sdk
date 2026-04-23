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
        "Validates that the connector's XSOAR handler capabilities and "
        "sub-capabilities license union contains the integration's supportedModules."
    )
    rationale = (
        "The connector's capabilities define which licenses are required. "
        "The integration's supportedModules defines which modules it supports. "
        "The connector's license set must be a superset of the integration's "
        "supportedModules to ensure proper license coverage."
    )
    error_message = (
        "Connector '{connector_id}': the integration '{integration_id}' has "
        "supportedModules {integration_modules} that are not covered by the "
        "connector's XSOAR capabilities license union {connector_licenses}. "
        "Missing modules: {missing_modules}"
    )
    related_field = "config.required_license"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Check that the connector's license union covers the integration's supportedModules.

        For each connector with a matched integration (via related_content):
        1. Collect the XSOAR handler's capability IDs
        2. For each capability ID, find the matching CapabilityData
        3. Union all required_license from capabilities and sub-capabilities
        4. Check that integration.supportedModules is a subset
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            if not connector.xsoar_handlers or connector.related_content is None:
                continue

            integration = connector.related_content
            integration_modules: Set[str] = set(
                getattr(integration, "supportedModules", None) or []
            )
            if not integration_modules:
                # Integration has no supportedModules -- nothing to validate
                continue

            # Collect XSOAR handler capability IDs
            xsoar_capability_ids: Set[str] = set()
            for handler in connector.xsoar_handlers:
                for cap in handler.capabilities:
                    xsoar_capability_ids.add(cap.id)

            # Build capability lookup
            capability_by_id = {c.id: c for c in connector.capabilities}

            # Collect the union of all required_license from capabilities + sub-capabilities
            connector_licenses: Set[str] = set()
            for cap_id in xsoar_capability_ids:
                cap_data = capability_by_id.get(cap_id)
                if not cap_data:
                    continue
                # Capability-level license
                if cap_data.config and cap_data.config.required_license:
                    connector_licenses.update(cap_data.config.required_license)
                # Sub-capability-level license
                for sub_cap in cap_data.sub_capabilities:
                    if sub_cap.required_license:
                        connector_licenses.update(sub_cap.required_license)

            if not connector_licenses:
                # No licenses defined on connector capabilities -- skip
                continue

            # Check that integration's supportedModules is a subset of connector licenses
            missing_modules = integration_modules - connector_licenses
            if missing_modules:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            integration_id=getattr(integration, "object_id", "unknown"),
                            integration_modules=sorted(integration_modules),
                            connector_licenses=sorted(connector_licenses),
                            missing_modules=sorted(missing_modules),
                        ),
                        content_object=connector,
                    )
                )

        return results
