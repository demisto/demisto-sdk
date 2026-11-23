from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

EXPECTED_TEAM = "xsoar"
XSOAR_CONTENT_MAINTAINER = "@xsoar-content"


class IsHandlerOwnershipFieldsAlignValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO156"
    description = (
        "Validates that every XSOAR handler's metadata.ownership fields align: "
        "team must equal 'xsoar' and maintainers must contain "
        "'@xsoar-content'."
    )
    rationale = (
        "XSOAR handlers must self-declare their ownership so the platform, "
        "CODEOWNERS routing, and downstream tooling can attribute them to the "
        "XSOAR content team. This mirrors the connector-level rule (CO100) but "
        "asserts the same invariant at handler granularity — a handler is "
        "XSOAR-classified via HandlerData.is_xsoar (OR of module=='xsoar', "
        "team=='xsoar', or '@xsoar-content' in maintainers), and this "
        "validator enforces the two ownership signals directly. Contains-check "
        "on maintainers (matching CO100) allows co-maintainers alongside "
        "'@xsoar-content'."
    )
    error_message = (
        "Handler '{handler_id}' has misaligned metadata.ownership: " "{problems}."
    )
    related_field = "metadata.ownership"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Flag any XSOAR-classified handler whose ownership is misaligned.

        Two independent checks per handler:

        1. ``metadata.ownership.team`` must equal ``"xsoar"``.
        2. ``metadata.ownership.maintainers`` must contain
           ``"@xsoar-content"`` (contains-check, matching CO100; co-maintainers
           are permitted).

        Both checks are evaluated and aggregated into a single per-handler
        result so the connector author sees every ownership issue in one
        message. A separate ``ValidationResult`` is emitted per failing handler
        (not per connector), with ``path`` pointing at the offending
        ``handler.yaml``.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.xsoar_handlers:
                ownership = handler.metadata.ownership
                team = ownership.team
                maintainers = ownership.maintainers or []

                problems: List[str] = []
                if team != EXPECTED_TEAM:
                    problems.append(
                        f"team is '{team or ''}' (expected '{EXPECTED_TEAM}')"
                    )
                if XSOAR_CONTENT_MAINTAINER not in maintainers:
                    problems.append(
                        f"maintainers must contain '{XSOAR_CONTENT_MAINTAINER}' "
                        f"(current: {list(maintainers) or '[]'})"
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
