from __future__ import annotations

from typing import Iterable, List, Set

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Connector


# The 6 canonical capability slugs that XSOAR-migrated connectors must use.
# These are the slugified forms of the six capability buckets defined in the
# connectus migration mapper (see connectus/connectus_migration/connector_param_mapper.py
# lines 13–18). Every XSOAR-migrated handler's capability claim must resolve
# to one of these — either as a top-level capability id, or as a
# sub_capability nested under one of these top-level ids.
CANONICAL_CAPABILITY_IDS: frozenset[str] = frozenset(
    {
        "automation",
        "fetch-assets-and-vulnerabilities",
        "fetch-issues",
        "fetch-secrets",
        "log-collection",
        "threat-intelligence-enrichment",
    }
)


class IsCapabilityNameValidValidator(BaseValidator[ContentTypes]):
    error_code = "CO119"
    description = (
        "Validates that every capability id claimed by an XSOAR handler "
        "either matches one of the 6 canonical top-level capability ids, "
        "or is a sub_capability nested under one of those canonical ids."
    )
    rationale = (
        "XSOAR-migrated connectors classify their handlers into 6 well-known "
        "capability buckets (Automation, Fetch Issues, Log Collection, "
        "Threat Intelligence & Enrichment, Fetch Assets and Vulnerabilities, "
        "Fetch Secrets). Any handler claim that doesn't fit those buckets "
        "indicates a mis-named capability, a typo, or an architectural "
        "drift that breaks downstream tooling expecting the canonical set."
    )
    error_message = (
        "Connector '{connector_id}' has XSOAR handlers claiming capability "
        "ids that are not in the canonical set {canonical} (or nested as "
        "sub-capabilities under one of them):\n{handler_details}"
    )
    related_field = "capabilities"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Per-id strict check: every id in
        ``handler.capabilities[].id`` (for XSOAR handlers only, per Q1=a)
        must satisfy ONE of:
          1. Equal a top-level ``capabilities[].id`` whose value is in
             ``CANONICAL_CAPABILITY_IDS``.
          2. Equal a nested ``capabilities[].sub_capabilities[].id`` whose
             parent's ``id`` is in ``CANONICAL_CAPABILITY_IDS``
             (per Q2=a: sub-caps under non-canonical parents are invalid).

        Per Q3=b, we DO NOT flag non-canonical top-level entries declared
        in capabilities.yaml when no handler claims them — only handler
        claims that violate the rule produce errors.

        Issues for one connector are merged into ONE ValidationResult.
        """
        results: List[ValidationResult] = []
        for connector in content_items:
            # Build the set of ids that handlers are allowed to claim:
            # canonical top-level ids that are declared in capabilities.yaml,
            # plus sub_capability ids whose parent is canonical.
            allowed_top: Set[str] = set()
            allowed_sub: Set[str] = set()
            for cap in connector.capabilities:
                if cap.id in CANONICAL_CAPABILITY_IDS:
                    allowed_top.add(cap.id)
                    for sub in cap.sub_capabilities:
                        allowed_sub.add(sub.id)
            allowed_all = allowed_top | allowed_sub

            handler_issues: List[str] = []
            for handler in connector.xsoar_handlers:
                bad_ids: List[str] = []
                for hcap in handler.capabilities:
                    if hcap.id not in allowed_all:
                        bad_ids.append(hcap.id)
                if bad_ids:
                    handler_issues.append(
                        f"handler '{handler.id}' claims non-canonical "
                        f"capability id(s): {sorted(bad_ids)}"
                    )

            if handler_issues:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            canonical=sorted(CANONICAL_CAPABILITY_IDS),
                            handler_details="\n".join(handler_issues),
                        ),
                        content_object=connector,
                    )
                )
        return results
