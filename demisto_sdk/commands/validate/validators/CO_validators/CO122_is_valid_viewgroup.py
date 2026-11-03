from __future__ import annotations

import re
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


def _normalize_id(value: str) -> str:
    """Normalize an id/name for lenient comparison.

    Lowercases and drops every non-alphanumeric character so that
    ``"Palo Alto Networks Threat Vault v2"``,
    ``"palo-alto-networks-threat-vault-v2"``,
    ``"palo_alto_networks_threat_vault_v2"``,
    ``"MITRE ATT&CK v2"`` vs ``"mitreattackv2"``, and
    ``"Mail Sender (New)"`` vs ``"mailsendernew"`` all collapse to the
    same canonical form.
    """
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


class IsValidViewgroupValidator(ConnectorsValidator[ContentTypes]):
    """CO122 - grouped-only. For each XSOAR handler:

    A. Short-circuit if the connector is not grouped.
    B. Unresolved XSOAR handler (``related_integration is None``) is an
       error (never silent-skip - matches CO120/CO121 directive).
    C. ``connection.view_groups[*].id`` MUST match
       ``handler.related_integration.object_id`` after normalization
       (lowercased with every non-alphanumeric character stripped).
       View-group ids are developer-facing so we tolerate stylistic
       drift as long as the ids collapse to the same canonical form.
    D. The matched view_group's ``label`` MUST equal
       ``handler.related_integration.display_name`` VERBATIM - the
       label is customer-facing (shown as the tile heading).

    Non-XSOAR handlers are skipped (out of team scope). Orphan
    view_groups (declared but not referenced by any XSOAR handler) are
    NOT flagged - they may belong to non-XSOAR handlers.
    """

    error_code = "CO122"
    description = (
        "Grouped-only. For each XSOAR handler in the connector, verify "
        "that connection.yaml declares a view_group whose id matches "
        "the handler's resolved integration id after alphanumeric-only "
        "normalization AND whose label equals the integration's "
        "display_name verbatim."
    )
    rationale = (
        "In grouped connectors, each XSOAR handler surfaces to users "
        "through a view_group (tile) on the connection page. The "
        "view_group label is customer-facing and MUST equal the "
        "integration display_name so the tile heading stays in "
        "lock-step with the integration UI. The view_group id is "
        "developer-facing and only needs to match the integration id "
        "after alphanumeric-only normalization (lowercased, every "
        "non-alphanumeric character stripped)."
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
    def _find_view_group_lenient(
        view_groups: List[ViewGroup], integration_id: str
    ) -> Optional[ViewGroup]:
        """Return the view_group whose id matches ``integration_id`` after
        normalization (case/space/dash/underscore/dot insensitive)."""
        target = _normalize_id(integration_id)
        for vg in view_groups:
            if _normalize_id(vg.id) == target:
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

        # Sub-rule C: view_group id must match the integration id
        # after normalization (case/space/dash/underscore/dot).
        matched = IsValidViewgroupValidator._find_view_group_lenient(
            view_groups, expected_id
        )
        if matched is None:
            issues.append(
                f"XSOAR handler '{handler.id}' expects a view_group whose "
                f"id normalizes to '{_normalize_id(expected_id)}' "
                f"(integration id '{expected_id}') in connection.yaml "
                f"view_groups, but none was found."
            )
            return issues

        # Sub-rule D: matched view_group's label MUST equal
        # display_name verbatim (customer-facing).
        if expected_label and matched.label != expected_label:
            issues.append(
                f"view_group '{matched.id}' has label='{matched.label}' "
                f"but must equal integration display_name "
                f"'{expected_label}' verbatim (XSOAR handler "
                f"'{handler.id}')."
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
