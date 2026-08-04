from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration

# Parameter names reserved by the connector platform. An integration that
# groups into a connector must not define parameters with these names, since
# the platform injects them (engine selection / instance identity) itself.
RESERVED_PARAM_NAMES = frozenset(
    {
        "engine",
        "engine_mode",
        "instance_name",
        "enginegroup",
    }
)


class NoReservedParamNamesValidator(BaseValidator[ContentTypes]):
    error_code = "CO190"
    description = (
        "Ensure an integration does not define parameters using names "
        "reserved by the connector platform (engine, engine_mode, "
        "instance_name, enginegroup)."
    )
    rationale = (
        "The connector platform injects the engine / instance-identity "
        "parameters itself. An integration that declares a parameter with one "
        "of these reserved names collides with the platform-managed field."
    )
    error_message = (
        "The integration uses reserved parameter name(s): "
        "{reserved}. Rename these parameters to avoid colliding with "
        "platform-managed connector fields."
    )
    related_field = "configuration"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for integration in content_items:
            reserved_used = sorted(
                {
                    param.name
                    for param in integration.params
                    if param.name.lower() in RESERVED_PARAM_NAMES
                }
            )
            if reserved_used:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            integration_id=integration.object_id,
                            reserved=", ".join(map(repr, reserved_used)),
                        ),
                        content_object=integration,
                    )
                )

        return results
