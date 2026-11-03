from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

# The 6 allowed XSOAR capability ids. A parent capability's id must be exactly
# one of these; a sub-capability's base prefix (the part before the first "_",
# since sub-capability ids follow "<capability-id>_<integration>") must be one
# of these.
ALLOWED_CAPABILITY_IDS = frozenset(
    {
        "automation-and-remediation",
        "log-collection",
        "fetch-issues",
        "fetch-assets-and-vulnerabilities",
        "threat-intelligence-and-enrichment",
        "fetch-secrets",
    }
)


def base_capability_id(sub_capability_id: str) -> str:
    """Return the base capability id of a sub-capability id.

    Sub-capability ids follow the pattern ``<capability-id>_<integration>``
    (e.g. ``fetch-issues_akamai-waf-siem`` -> ``fetch-issues``). None of the
    allowed base ids contain an underscore, so the base id is everything before
    the first underscore.
    """
    return sub_capability_id.split("_", 1)[0]


class IsCapabilityNameValidValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO110"
    description = (
        "Validates that every XSOAR-owned capability and sub-capability uses "
        "one of the allowed XSOAR capability ids."
    )
    rationale = (
        "XSOAR capabilities are drawn from a fixed, well-known set. An "
        "XSOAR-owned capability (or sub-capability) whose id is not one of the "
        "allowed ids will not map to any platform capability. Ownership is "
        "determined via the handler 'module: xsoar' field; non-XSOAR "
        "capabilities are left to their own naming and skipped."
    )
    error_message = (
        "Connector '{connector_id}' has XSOAR-owned capabilities with invalid "
        "ids: {invalid}. Allowed capability ids: {allowed}."
    )
    related_field = "capabilities"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CAPABILITIES]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            invalid: List[str] = []

            for capability in connector.capabilities:
                # Parent capability: id must be exactly one of the allowed ids.
                if self._is_xsoar_owned(connector, capability.id):
                    if capability.id not in ALLOWED_CAPABILITY_IDS:
                        invalid.append(capability.id)

                # Sub-capabilities: base prefix must be one of the allowed ids.
                for sub_capability in capability.sub_capabilities:
                    if not self._is_xsoar_owned(connector, sub_capability.id):
                        continue
                    if base_capability_id(sub_capability.id) not in (
                        ALLOWED_CAPABILITY_IDS
                    ):
                        invalid.append(sub_capability.id)

            if invalid:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            invalid=", ".join(map(repr, sorted(invalid))),
                            allowed=", ".join(sorted(ALLOWED_CAPABILITY_IDS)),
                        ),
                        content_object=connector,
                        path=connector.capabilities_file.file_path,
                    )
                )

        return results

    @staticmethod
    def _is_xsoar_owned(connector: ContentTypes, capability_id: str) -> bool:
        """Whether the given capability/sub-capability id is XSOAR-owned.

        Ownership is recorded on the capability-handler mapping, which sets
        ``is_xsoar`` when at least one subscribing handler is XSOAR-related
        (``module: xsoar`` and ``team: xsoar``).
        """
        mapping = connector.capability_handler_map.get(capability_id)
        return bool(mapping and mapping.is_xsoar)
