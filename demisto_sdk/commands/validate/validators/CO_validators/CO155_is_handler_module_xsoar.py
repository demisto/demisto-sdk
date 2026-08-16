from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

EXPECTED_MODULE = "xsoar"


class IsHandlerModuleXsoarValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO155"
    description = (
        "Validates that every XSOAR handler declares " "`metadata.module: xsoar`."
    )
    rationale = (
        "The unified-connectors schema does not require the `module` field "
        "to be present, but XSOAR handlers must set it to `xsoar` so the "
        "platform, downstream tooling and cross-integration validators can "
        "reliably identify XSOAR-owned handlers. `HandlerData.is_xsoar` "
        'accepts any one of `module=="xsoar"`, `team=="xsoar"`, or '
        "`@xsoar-content` in `maintainers` to widen collection, but the "
        "canonical, self-declaring signal is `metadata.module: xsoar`."
    )
    error_message = (
        "Handler '{handler_id}' is an XSOAR handler but its "
        "metadata.module is '{actual}' (expected 'xsoar')."
    )
    related_field = "metadata.module"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Flag any XSOAR-classified handler whose metadata.module is not
        exactly ``xsoar``.

        A handler is XSOAR-classified when :pyattr:`HandlerData.is_xsoar` is
        True (any one of ``module == "xsoar"``, ``team == "xsoar"``, or
        ``"@xsoar-content" in maintainers``). This validator asserts that
        the canonical self-declaring signal — ``metadata.module`` — is
        present and equals ``xsoar``.

        A separate ``ValidationResult`` is emitted per failing handler so
        consumers can act on each handler individually. Each result's
        ``path`` points at the offending ``handler.yaml``.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.xsoar_handlers:
                actual = handler.metadata.module
                if actual == EXPECTED_MODULE:
                    continue

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            handler_id=handler.id,
                            actual=actual if actual is not None else "",
                        ),
                        content_object=connector,
                        path=handler.file_path,
                    )
                )

        return results
