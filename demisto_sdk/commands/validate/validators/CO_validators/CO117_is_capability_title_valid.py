from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

# Connector words that stay lowercase in a capability title (never the first
# word). The known capability ids only ever use "and".
LOWERCASE_WORDS = {"and"}


def expected_title(capability_id: str) -> str:
    """Return the expected Title Case title for a capability id.

    The id is hyphen-delimited; each segment becomes a word. Every word is
    capitalized except connector words in ``LOWERCASE_WORDS`` (e.g. "and"),
    which stay lowercase - but the first word is always capitalized.

    Examples:
        fetch-issues                       -> "Fetch Issues"
        automation-and-remediation         -> "Automation and Remediation"
        threat-intelligence-and-enrichment -> "Threat Intelligence and Enrichment"
    """
    words = capability_id.split("-")
    titled: List[str] = []
    for index, word in enumerate(words):
        if index != 0 and word in LOWERCASE_WORDS:
            titled.append(word)
        else:
            titled.append(word.capitalize())
    return " ".join(titled)


class IsCapabilityTitleValidValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO117"
    description = (
        "Validates that each capability's title is the exact Title Case of its "
        "id (hyphen-delimited words capitalized, with the connector word 'and' "
        "kept lowercase). For example, 'automation-and-remediation' must have "
        "the title 'Automation and Remediation'."
    )
    rationale = (
        "Capability titles are customer-facing labels derived from their ids. "
        "A consistent, deterministic Title Case keeps the product UI uniform "
        "and prevents ad-hoc or mismatched capability labels."
    )
    error_message = (
        "Connector '{connector_id}' has capabilities whose title does not match "
        "the expected Title Case of their id: {details}."
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
            details: List[str] = []

            # Parent capabilities only. Sub-capability titles are the backing
            # integration's display name (governed by CO194), not a title-cased
            # id, so they are intentionally excluded here.
            for capability in connector.capabilities:
                expected = expected_title(capability.id)
                if capability.title != expected:
                    details.append(
                        f"'{capability.id}' has title "
                        f"{capability.title!r} but expected {expected!r}"
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
                        path=connector.capabilities_file.file_path,
                    )
                )

        return results
