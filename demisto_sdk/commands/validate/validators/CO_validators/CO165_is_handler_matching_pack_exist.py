from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsHandlerMatchingPackExistValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO165"
    description = (
        "Validates that each XSOAR handler declares an xsoar-pack-id "
        "triggering label and that the label matches the pack that owns "
        "the handler's referenced integration."
    )
    rationale = (
        "Every XSOAR handler declares two triggering labels: "
        "``xsoar-integration-id`` (checked by CO164) and ``xsoar-pack-id``. "
        "This validator enforces consistency between the pack-id label and "
        "the actual pack that owns the resolved integration "
        "(``handler.related_integration.pack_id``). A drift between the two "
        "means the handler's label was manually edited or copy-pasted "
        "incorrectly and the platform will route to the wrong pack. "
        "Consistency-based (uses already-resolved graph data; no additional "
        "queries)."
    )
    error_message = "Handler '{handler_id}': {problem}."
    related_field = "triggering.labels"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Check the xsoar-pack-id label of every XSOAR handler.

        Three failure cases (checked in this order; first match wins per
        handler):

        1. ``xsoar-pack-id`` label is missing from ``triggering.labels``.
        2. The handler's ``related_integration`` is not resolved -
           consistency cannot be verified (CO164 will also flag this; we
           surface it here as an unverifiable pack reference).
        3. ``handler.xsoar_pack_id`` does not equal
           ``handler.related_integration.pack_id`` - the label references a
           different pack than the one that actually contains the integration.

        A separate ``ValidationResult`` is emitted per failing handler; each
        result's ``path`` points at the offending ``handler.yaml``.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.xsoar_handlers:
                declared_pack_id = handler.xsoar_pack_id
                integration = handler.related_integration

                if not declared_pack_id:
                    problem = "missing xsoar-pack-id in triggering.labels"
                elif integration is None:
                    problem = (
                        f"xsoar-pack-id '{declared_pack_id}' cannot be "
                        f"verified because the handler's related integration "
                        f"is not resolved (see also CO164)"
                    )
                else:
                    actual_pack_id = integration.pack_id
                    if declared_pack_id != actual_pack_id:
                        problem = (
                            f"xsoar-pack-id '{declared_pack_id}' does not "
                            f"match the pack that owns integration "
                            f"'{integration.object_id}' "
                            f"(expected '{actual_pack_id}')"
                        )
                    else:
                        continue

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            handler_id=handler.id,
                            problem=problem,
                        ),
                        content_object=connector,
                        path=handler.file_path,
                    )
                )

        return results
