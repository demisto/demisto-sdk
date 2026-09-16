from __future__ import annotations

import re
from typing import Iterable, List, Optional

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
    SubCapability,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


def normalize_integration_id(integration_id: str) -> str:
    """Normalize an integration id into the sub-capability id suffix.

    Sub-capability ids are shaped ``<capability_id>_<slug>`` where ``<slug>``
    is derived deterministically from the backing XSOAR integration id. The
    rule mirrors what the UCP manifest generator emits and what content
    authors put on disk today:

    1. Lowercase the integration id.
    2. Replace any run of characters outside ``[a-z0-9]`` with a single ``-``.
       (Spaces, ``.``, ``&``, ``?``, ``(``, ``)``, ``-``, etc. all collapse.)
    3. Trim leading/trailing dashes.

    This is intentionally stricter than :func:`CO103.title_to_slug` (which
    preserves ``.`` and ``?``) because sub-capability slugs on disk drop
    those characters — the two slug functions have different inputs
    (connector title vs integration id) and different current conventions.

    Examples::

        "AWS - Athena - Beta"          -> "aws-athena-beta"
        "Cortex XDR - IOC"             -> "cortex-xdr-ioc"
        "Have I Been Pwned? V2"        -> "have-i-been-pwned-v2"
        "Mail Sender (New)"            -> "mail-sender-new"
        "OpenCTI Feed 4.X"             -> "opencti-feed-4-x"
        "Tenable.io"                   -> "tenable-io"
        "abuse.ch SSL Blacklist Feed"  -> "abuse-ch-ssl-blacklist-feed"

    ``mitre-attack-v2`` (from ``MITRE ATT&CK v2``, where the stylized ``&``
    substitutes for the letter ``A``) is NOT reproducible by this
    mechanical rule; the mechanical form is ``mitre-att-ck-v2``. Since
    sub-capability ids are immutable after publish, this validator only
    runs on newly ADDED connectors (see :pyattr:`expected_git_statuses`),
    so any existing non-mechanical ids are grandfathered in.
    """
    return re.sub(r"[^a-z0-9]+", "-", integration_id.lower()).strip("-")


class IsSubCapabilityIdDerivedValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO113"
    description = (
        "Validates that each sub-capability in a NEW grouped connector has an "
        "id derived as '<capability_id>_<normalized_integration_id>'."
    )
    rationale = (
        "Sub-capability ids are derived deterministically from the parent "
        "capability and the integration they belong to. A sub-capability id "
        "that does not follow '<capability_id>_<normalized_integration_id>' "
        "indicates the capabilities.yaml drifted from the handler/integration. "
        "Because sub-capability ids are immutable after publish (renaming one "
        "breaks existing customer instances), this rule is only enforced on "
        "newly added connectors. Sub-capability titles — which are safe to "
        "change any time — are separately governed by CO194 on every grouped "
        "connector, regardless of git status."
    )
    error_message = (
        "Grouped connector '{connector_id}' has invalid sub-capabilities: " "{details}."
    )
    related_field = "capabilities"
    is_auto_fixable = False
    # Only run on brand-new connectors: an existing sub-capability id cannot
    # be changed without breaking upgrades of existing customer instances,
    # so drift on already-published connectors is intentionally grandfathered.
    # Title drift is caught separately by CO194.
    expected_git_statuses = [GitStatuses.ADDED]
    related_file_type = [RelatedFileType.CONNECTOR_CAPABILITIES]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            # Grouped-only: short-circuit for non-grouped connectors.
            if not (connector.settings and connector.settings.grouped):
                continue

            details: List[str] = []

            for capability in connector.capabilities:
                for sub_capability in capability.sub_capabilities:
                    details.extend(
                        self._check_sub_capability(
                            connector, capability.id, sub_capability
                        )
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

    def _check_sub_capability(
        self,
        connector: ContentTypes,
        capability_id: str,
        sub_capability: SubCapability,
    ) -> List[str]:
        """Validate a single sub-capability's id derivation.

        Iterates from the capabilities.yaml side. The subscribing handler
        (if any) provides the integration id used to derive the expected
        sub-capability id.

        The "at least one subscribing handler" requirement is intentionally
        NOT enforced here -- that rule is handled within UCP itself. The
        structural id pattern is still enforced even when no handler
        subscribes, so a mis-derived id is never accepted.

        Title correctness is enforced by CO194 (grouped connectors, all git
        statuses); this validator only checks the immutable id.
        """
        details: List[str] = []
        sub_id = sub_capability.id

        # Structural pattern: id must be '<capability_id>_<segment>' with a
        # non-empty segment. This holds regardless of handler resolution.
        prefix = f"{capability_id}_"
        segment = sub_id[len(prefix) :] if sub_id.startswith(prefix) else None
        if not segment:
            details.append(
                f"sub-capability '{sub_id}' id must follow the pattern "
                f"'{capability_id}_<normalized_integration_id>'"
            )
            # Without a valid prefix/segment we cannot derive anything further.
            return details

        handler = self._subscribing_handler(connector, sub_id)
        if handler is None:
            # No handler subscribes to this sub-capability. The "must have a
            # subscriber" rule is handled within UCP itself; here we only
            # verified the structural pattern above, so nothing more to check.
            return details

        integration_id = handler.xsoar_integration_id
        if integration_id:
            expected_id = f"{capability_id}_{normalize_integration_id(integration_id)}"
            if sub_id != expected_id:
                details.append(
                    f"sub-capability '{sub_id}' id must be '{expected_id}' "
                    f"(derived from integration '{integration_id}')"
                )

        return details

    @staticmethod
    def _subscribing_handler(
        connector: ContentTypes, sub_capability_id: str
    ) -> Optional[HandlerData]:
        """Return the first handler subscribing to the given sub-capability.

        Uses the connector's ``capability_handler_map`` (keyed by both
        capability and sub-capability ids). Returns ``None`` when no handler
        subscribes to the sub-capability.
        """
        mapping = connector.capability_handler_map.get(sub_capability_id)
        if not mapping or not mapping.handler_ids:
            return None

        handler_id = mapping.handler_ids[0]
        return next((h for h in connector.handlers if h.id == handler_id), None)
