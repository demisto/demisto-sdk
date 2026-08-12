from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

CANONICAL_WORKLOADS = frozenset({"xsoar-automationhub-runner", "xsoar-pod"})


class IsValidWorkloadsValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO162"
    description = (
        "Validates that every auth_option's workloads list equals the "
        "canonical set {xsoar-automationhub-runner, xsoar-pod} (order "
        "insensitive), and that no capability declares the anonymous "
        "capability-level workloads shape."
    )
    rationale = (
        "XSOAR handlers execute on a fixed set of platform workloads. Every "
        "auth_option a handler declares must run on both workloads so the "
        "platform can schedule the handler on either. The anonymous "
        "capability-level workloads shape (``capabilities[].workloads`` "
        "without auth_options) is a legal schema variant but is never used "
        "by XSOAR handlers, so its presence indicates a migration mistake."
    )
    error_message = "Handler '{handler_id}' has invalid workloads: {problems}."
    related_field = "capabilities[].auth_options[].workloads"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """For each XSOAR handler, validate every workloads list.

        Two check families per capability:

        1. Capability-level workloads (the anonymous ``auth: none`` shape)
           must be absent - XSOAR handlers always declare workloads under
           ``auth_options``. A non-empty capability-level workloads list is
           a hard fail.
        2. Every ``auth_options[].workloads`` must equal the canonical set
           ``{xsoar-automationhub-runner, xsoar-pod}`` (order-insensitive).
           Missing / empty lists fail, mismatched sets fail.

        Per-handler aggregated result. Path points at the offending
        ``handler.yaml``.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.xsoar_handlers:
                problems: List[str] = []

                for cap in handler.capabilities:
                    if cap.workloads:
                        problems.append(
                            f"capability '{cap.id}' declares "
                            f"capability-level workloads "
                            f"{list(cap.workloads)}; XSOAR handlers must "
                            f"declare workloads under auth_options instead"
                        )

                    for ao in cap.auth_options:
                        actual = set(ao.workloads or [])
                        if actual != CANONICAL_WORKLOADS:
                            problems.append(
                                f"capability '{cap.id}' auth_option "
                                f"'{ao.id}' has workloads "
                                f"{sorted(actual) if actual else '[]'} "
                                f"(expected {sorted(CANONICAL_WORKLOADS)})"
                            )

                if problems:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                handler_id=handler.id,
                                problems="; ".join(problems),
                            ),
                            content_object=connector,
                            path=handler.file_path,
                        )
                    )

        return results
