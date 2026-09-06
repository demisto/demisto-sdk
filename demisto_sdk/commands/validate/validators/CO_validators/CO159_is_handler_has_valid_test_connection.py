from __future__ import annotations

from typing import Iterable, List, Optional

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerTestConnection,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

CANONICAL_TYPE = "service"
CANONICAL_SERVICE = "xsoar"
CANONICAL_ENDPOINT = "/settings/integration/connector/verification"


class IsHandlerHasValidTestConnectionValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO159"
    description = (
        "Validates that every XSOAR handler carries the canonical "
        "test_connection AND test_connection_metro blocks: "
        "{type: service, service: xsoar, "
        "endpoint: /settings/integration/connector/verification}, "
        "with no additional fields set."
    )
    rationale = (
        "The XSOAR platform routes handler connection-verification requests "
        "through a fixed service endpoint. Both `test_connection` (the base "
        "block) and `test_connection_metro` (the multi-tenant override) must "
        "declare the same canonical shape so the platform, the migration "
        "generator, and metro deployments all agree on how to test the "
        "handler. Any deviation (missing block, wrong type/service/endpoint, "
        "or extra fields like `host`/`headers`) is a bug that breaks "
        "connection verification."
    )
    error_message = (
        "Handler '{handler_id}' has invalid test_connection wiring: " "{problems}."
    )
    related_field = "test_connection"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Validate both test_connection and test_connection_metro on every
        XSOAR handler.

        Each block is checked independently against the canonical shape via
        :meth:`_check_block`. Missing ``test_connection_metro`` (the field is
        ``Optional`` at the model layer with a default of ``None``) is itself
        a failure - the metro override is mandatory per manifest.

        Both blocks' problems on the same handler are aggregated into a
        single per-handler result so authors see everything at once. Path
        points at the offending ``handler.yaml``.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.xsoar_handlers:
                problems: List[str] = []

                problems.extend(
                    self._check_block("test_connection", handler.test_connection)
                )

                if handler.test_connection_metro is None:
                    problems.append("test_connection_metro block is missing")
                else:
                    problems.extend(
                        self._check_block(
                            "test_connection_metro",
                            handler.test_connection_metro,
                        )
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

    @staticmethod
    def _check_block(
        block_name: str, block: Optional[HandlerTestConnection]
    ) -> List[str]:
        """Return a list of ``"block.field ..."`` problem strings for a single
        test-connection block.

        A ``None`` block is treated as fully-invalid (every canonical field
        missing) so upstream callers can pass in either the required
        ``test_connection`` (never None on the model) or the optional
        ``test_connection_metro`` (may be None) uniformly. In practice
        upstream handles the metro-None case with its own message and skips
        this call.
        """
        if block is None:
            return [
                f"{block_name}.type is missing (expected '{CANONICAL_TYPE}')",
                f"{block_name}.service is missing " f"(expected '{CANONICAL_SERVICE}')",
                f"{block_name}.endpoint is missing "
                f"(expected '{CANONICAL_ENDPOINT}')",
            ]

        problems: List[str] = []
        if block.type != CANONICAL_TYPE:
            problems.append(
                f"{block_name}.type is "
                f"'{block.type if block.type is not None else ''}' "
                f"(expected '{CANONICAL_TYPE}')"
            )
        if block.service != CANONICAL_SERVICE:
            problems.append(
                f"{block_name}.service is "
                f"'{block.service if block.service is not None else ''}' "
                f"(expected '{CANONICAL_SERVICE}')"
            )
        if block.endpoint != CANONICAL_ENDPOINT:
            problems.append(
                f"{block_name}.endpoint is "
                f"'{block.endpoint if block.endpoint is not None else ''}' "
                f"(expected '{CANONICAL_ENDPOINT}')"
            )
        if block.host is not None:
            problems.append(f"{block_name}.host must be omitted (found '{block.host}')")
        if block.headers is not None:
            problems.append(
                f"{block_name}.headers must be omitted " f"(found {block.headers})"
            )
        return problems
