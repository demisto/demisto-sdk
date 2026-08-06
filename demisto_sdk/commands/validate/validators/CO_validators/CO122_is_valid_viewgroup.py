from __future__ import annotations

from typing import Iterable, List, Optional

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
    ViewGroup,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsValidViewgroupValidator(ConnectorsValidator[ContentTypes]):
    """CO122 - grouped-only. For each XSOAR handler:

    A. Short-circuit if the connector is not grouped.
    B. Unresolved XSOAR handler (``related_integration is None``) is an
       error (never silent-skip - matches CO120/CO121 directive).
    C. ``connection.view_groups[*].id`` MUST include
       ``handler.related_integration.object_id``.
    D. The matched view_group's ``label`` MUST equal
       ``handler.related_integration.display_name``.

    Non-XSOAR handlers are skipped (out of team scope). Orphan
    view_groups (declared but not referenced by any XSOAR handler) are
    NOT flagged - they may belong to non-XSOAR handlers.
    """

    error_code = "CO122"
    description = (
        "Grouped-only. For each XSOAR handler in the connector, verify "
        "that connection.yaml declares a view_group whose id matches the "
        "handler's resolved integration id AND whose label equals the "
        "integration's display_name."
    )
    rationale = (
        "In grouped connectors, each XSOAR handler surfaces to users "
        "through a view_group (tile) on the connection page. The "
        "view_group id must match the handler's integration id (that's "
        "how field / profile bindings resolve at runtime), and the "
        "view_group label must match the integration display_name so the "
        "tile heading and the integration UI stay in lock-step."
    )
    error_message = (
        "Grouped connector '{connector_id}' has invalid view_group " "wiring: {issues}"
    )
    related_field = "view_groups"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CONNECTION]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_view_group(
        view_groups: List[ViewGroup], vg_id: str
    ) -> Optional[ViewGroup]:
        for vg in view_groups:
            if vg.id == vg_id:
                return vg
        return None

    @staticmethod
    def _handler_issues(
        handler: HandlerData, view_groups: List[ViewGroup]
    ) -> List[str]:
        """Return a list of human-readable issues for one XSOAR handler."""
        issues: List[str] = []

        # Sub-rule B: unresolved XSOAR handler is an error.
        integration = handler.related_integration
        if integration is None:
            issues.append(
                f"XSOAR handler '{handler.id}' has no resolved "
                f"integration; cannot verify view_group binding."
            )
            return issues

        expected_id = integration.object_id
        expected_label = integration.display_name

        # Sub-rule C: view_group id must match the integration id.
        matched = IsValidViewgroupValidator._find_view_group(view_groups, expected_id)
        if matched is None:
            issues.append(
                f"XSOAR handler '{handler.id}' expects a view_group with "
                f"id='{expected_id}' (integration id) in "
                f"connection.yaml view_groups, but none was found."
            )
            return issues

        # Sub-rule D: matched view_group's label must equal display_name.
        if expected_label and matched.label != expected_label:
            issues.append(
                f"view_group '{expected_id}' has label='{matched.label}' "
                f"but must equal integration display_name "
                f"'{expected_label}' (XSOAR handler '{handler.id}')."
            )

        return issues

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            # Sub-rule A: grouped-only short-circuit.
            if not (connector.settings and connector.settings.grouped):
                continue

            connection = connector.connection
            view_groups = connection.view_groups if connection else []

            all_issues: List[str] = []
            for handler in connector.handlers:
                if not handler.is_xsoar:
                    continue
                all_issues.extend(self._handler_issues(handler, view_groups))

            if all_issues:
                path = (
                    connector.connection_file.file_path
                    if connector.connection_file
                    else connector.path
                )
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            issues="; ".join(all_issues),
                        ),
                        content_object=connector,
                        path=path,
                    )
                )

        return results
