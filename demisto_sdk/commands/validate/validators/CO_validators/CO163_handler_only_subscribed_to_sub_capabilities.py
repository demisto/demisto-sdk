"""CO163 - HandlerOnlySubscribedToSubCapabilitiesValidator.

**Grouped only.** Per §3.8 rule 3 of the standard connector guide,
handlers in a grouped connector MUST subscribe to
sub-capabilities only - never to bare PARENT capabilities.

The bare-parent case in a grouped connector is a UI/BE contract
error: parents are containers whose per-tile lifecycle is owned by
each specific sub-capability (one sub-capability per integration).
A handler subscribed to the parent id has no unambiguous integration
target, breaking the same routing invariant CO168's rewritten spec
(``IsActionScopedToSingleIntegration``) documents for actions.

**Data-driven parent detection** (same approach we planned for
CO168's grouped-shape branch): a cap id is considered a "parent"
when it appears as a top-level id in ``connector.capabilities`` AND
that entry has a non-empty ``sub_capabilities`` list. Everything
else (sub-cap ids, leaves without children, unknown ids) is not
flagged. Unknown ids are CO115's / CO113's concern - CO163 stays
narrow.

**Short-circuit** for non-grouped connectors: standard connectors
don't use the sub-capability concept, so this rule is
grouped-only. Mirrors the ``if not (connector.settings and
connector.settings.grouped): continue`` pattern used by
CO111/CO112/CO113/CO119/CO124/CO144/CO194.

**Scope:** applies to ALL handlers, not just XSOAR - grouped
connectors are XSOAR-only per CO111, but the check is
ownership-agnostic (a hypothetical non-XSOAR handler with a bare
parent id would still corrupt the same routing invariant).

**Per-finding granularity:** one ``ValidationResult`` per (handler,
parent_cap_id) pair. A handler subscribed to two parent ids fires
twice; dedup key = ``(handler.id, cap_id)``.

**Structural complement of the deferred CO168:** CO163 is the
POSITIVE-side rule ("handler subscriptions must be sub-caps"),
CO168 is the NEGATIVE-side rule for actions ("actions must
be scoped to a single integration"). Shipping CO163 alone still
catches most of the grouped-connector routing bugs even before
CO168 lands, because a handler subscribed only to sub-caps
naturally has its actions on those sub-caps.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Set

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class HandlerOnlySubscribedToSubCapabilitiesValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO163"
    description = (
        "Grouped-only. Every handler's `capabilities[].id` MUST be a "
        "sub-capability id, never a bare parent capability id. Parent "
        "status is data-driven: any entry in the connector's "
        "capabilities registry with a non-empty sub_capabilities list "
        "is treated as a parent (per §3.8 rule 3)."
    )
    rationale = (
        "In a grouped connector, each sub-capability corresponds to "
        "one integration/tile; the parent is a UI grouping container "
        "only. A handler subscribed to the parent has no unambiguous "
        "integration target, so BE routing (fetch dispatch, action "
        "execution, credentials binding) becomes non-deterministic. "
        "Every handler must pin its subscription to the specific "
        "sub-capability that owns it."
    )
    error_message = (
        "Connector '{connector_id}' handler '{handler_id}' is "
        "subscribed to bare parent capability '{cap_id}' (which has "
        "{n_sub_caps} sub-capabilities: {sub_cap_ids}). In a grouped "
        "connector, handlers must subscribe to a specific "
        "sub-capability, not the parent - move the subscription to "
        "the sub-capability that owns this handler's integration."
    )
    related_field = "capabilities"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for connector in content_items:
            # Grouped-only short-circuit (mirrors CO111 / CO112 /
            # CO113 / CO119 / CO124 / CO144 / CO194).
            if not (connector.settings and connector.settings.grouped):
                continue
            results.extend(self._check_connector(connector))
        return results

    # ------------------------------------------------------------------
    # Per-connector check
    # ------------------------------------------------------------------

    def _check_connector(self, connector: Connector) -> List[ValidationResult]:
        # Build a map of parent-cap id -> list of sub-cap ids (for the
        # error message) for every parent (i.e. cap with non-empty
        # sub_capabilities). Non-parents are absent from the map, so a
        # dict lookup naturally short-circuits the check.
        parent_to_sub_ids = {
            cap.id: [sub.id for sub in cap.sub_capabilities]
            for cap in connector.capabilities
            if cap.sub_capabilities
        }

        if not parent_to_sub_ids:
            # Grouped connector with no declared parents - nothing to
            # flag. (Would also mean CO112 fires, but CO163 stays
            # narrow.)
            return []

        results: List[ValidationResult] = []
        for handler in connector.handlers:
            # Dedupe per (handler, cap_id) so a handler with the same
            # parent id listed twice only fires once.
            seen: Set[str] = set()
            for handler_cap in handler.capabilities:
                cap_id = handler_cap.id
                if cap_id in seen:
                    continue
                sub_ids = parent_to_sub_ids.get(cap_id)
                if sub_ids is None:
                    # Not a parent id (either a valid sub-cap id, a
                    # leaf, or an unknown id). Not CO163's concern.
                    continue
                seen.add(cap_id)
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            handler_id=handler.id,
                            cap_id=cap_id,
                            n_sub_caps=len(sub_ids),
                            sub_cap_ids=", ".join(sub_ids),
                        ),
                        content_object=connector,
                        path=self._handler_path(handler),
                    )
                )
        return results

    @staticmethod
    def _handler_path(handler: HandlerData) -> Optional[Path]:
        """Best-effort path to the handler's ``handler.yaml`` so the
        per-handler ignore chain
        (``[file:<handler-folder>/handler.yaml]``) resolves. Mirrors
        CO155 / CO156 / CO159 / CO170.
        """
        return handler.file_path
