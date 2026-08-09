from __future__ import annotations

from typing import Iterable, List, Optional

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerCapability,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

# Mapping of fetch base capability id -> required action.type.
# Only the four stateful fetch families are required to declare their
# reset action. ``fetch-secrets`` is stateless so it's intentionally
# omitted, and ``automation-and-remediation`` is NOT a fetch capability
# so it is NOT required to declare any action (handlers may still
# declare optional actions on it — CO161 only enforces required ones).
REQUIRED_ACTION_BY_BASE_CAP: dict = {
    "fetch-issues": "reset_incidents_last_run",
    "log-collection": "reset_events_last_run",
    "fetch-assets-and-vulnerabilities": "reset_assets_last_run",
    "threat-intelligence-and-enrichment": "reset_feed_last_run",
}


def _capability_base_id(cap_id: str) -> str:
    """Strip the ``_<suffix>`` from a namespaced capability id.

    Grouped connectors namespace capability ids as ``<base>_<integration>``
    (e.g. ``fetch-issues_akamai-waf-siem``). Standard non-grouped connectors
    use the bare base id (e.g. ``fetch-issues``). This helper returns the base
    portion in both cases so downstream logic can look up the required action.
    """
    return cap_id.split("_", 1)[0] if cap_id else ""


class IsFetchCapabilitiesContainActionsValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO161"
    description = (
        "Validates that every fetch-family capability the handler "
        "subscribes to declares its required reset-state action."
    )
    rationale = (
        "Fetch-type sub-capabilities are stateful (last-run cursors, event "
        "watermarks, feed offsets, incident IDs). The platform exposes a "
        "reset action per stateful capability so users can recover from "
        "bad state. A subscribed fetch capability that omits its required "
        "action leaves users without a recovery path. Base id -> required "
        "action mapping: "
        "fetch-issues -> reset_incidents_last_run; "
        "log-collection -> reset_events_last_run; "
        "fetch-assets-and-vulnerabilities -> reset_assets_last_run; "
        "threat-intelligence-and-enrichment -> reset_feed_last_run. "
        "fetch-secrets is stateless and has no required action. "
        "automation-and-remediation is not a fetch capability and is not "
        "required to declare any action (optional actions are permitted)."
    )
    error_message = (
        "Handler '{handler_id}' has capabilities missing required actions: "
        "{problems}."
    )
    related_field = "capabilities[].actions"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """For each XSOAR handler, verify every subscribed fetch-family
        capability contains an ``actions[].type`` matching its required
        action.

        Skips capabilities whose base id has no required action (e.g.
        ``fetch-secrets``, ``automation-and-remediation``, or any other
        non-fetch capability such as ``incident-response``).

        Per-handler aggregated result (one row per handler, listing every
        offending capability). Path points at the offending ``handler.yaml``.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.xsoar_handlers:
                problems: List[str] = []
                for cap in handler.capabilities:
                    problem = self._check_capability(cap)
                    if problem is not None:
                        problems.append(problem)

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
    def _check_capability(cap: HandlerCapability) -> Optional[str]:
        """Return a per-capability problem string, or ``None`` if the
        capability passes (either because its base id has no required action
        or because the required action is present).
        """
        base = _capability_base_id(cap.id)
        required = REQUIRED_ACTION_BY_BASE_CAP.get(base)
        if required is None:
            return None

        action_types = {a.type for a in cap.actions if a and a.type}
        if required in action_types:
            return None

        return (
            f"capability '{cap.id}' is missing action type "
            f"'{required}' (found {sorted(action_types) if action_types else '[]'})"
        )
