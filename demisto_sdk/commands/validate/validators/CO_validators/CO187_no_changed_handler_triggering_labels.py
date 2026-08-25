from __future__ import annotations

from typing import Iterable, List, Tuple, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

# The two `triggering.labels` keys this validator guards. Sourced through
# the `HandlerData.xsoar_integration_id` / `xsoar_pack_id` properties,
# which read `triggering.labels` None-safely.
_GUARDED_LABELS: Tuple[str, ...] = (
    "xsoar-integration-id",
    "xsoar-pack-id",
)


class NoChangedHandlerTriggeringLabelsValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO187"
    description = (
        "Breaking-change check: a handler's `triggering.labels` values "
        "for `xsoar-integration-id` and `xsoar-pack-id` must not change "
        "between versions. Diffs are performed per `handler.id` on "
        "handlers that exist in BOTH the prior and the new version; "
        "newly-added or removed handlers are not this validator's "
        "concern (CO176's `handler_id` family covers those)."
    )
    rationale = (
        "`xsoar-integration-id` binds a handler to the exact integration "
        "in the XSOAR content graph; `xsoar-pack-id` binds it to the "
        "owning pack. Changing either silently reroutes the handler to a "
        "different integration or pack, or unroutes it entirely — in "
        "both cases every downstream cross-repo validator (CO114, CO116, "
        "CO120, CO122, CO130, CO136, CO139, CO164, CO165, CO192) starts "
        "seeing a different (or missing) integration without any repo "
        "diff on the integration side. Both labels are free-form to "
        "schema and OPA, so this validator is the only guard."
    )
    error_message = (
        "Handler '{handler_id}' has changed triggering label(s) "
        "{changes}. These labels bind the handler to its integration "
        "and pack in the content graph and must remain stable across "
        "versions."
    )
    related_field = "triggering.labels.xsoar-integration-id,triggering.labels.xsoar-pack-id"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Per-handler equality diff of the two guarded triggering labels.

        Walks ALL handlers (not just `xsoar_handlers`) because rerouting
        is bidirectional: a non-xsoar handler whose `xsoar-integration-id`
        drifts is just as broken as an XSOAR one, and neither the schema
        nor OPA looks at these values. Absent handlers on either side
        are skipped (CO176 owns that surface).
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            old_connector = cast(ContentTypes, connector.old_base_content_object)
            if old_connector is None:
                continue

            old_by_id = {h.id: h for h in old_connector.handlers}

            for handler in connector.handlers:
                old_handler = old_by_id.get(handler.id)
                if old_handler is None:
                    continue  # newly-added handler

                changes = self._changed_labels(old_handler, handler)
                if not changes:
                    continue

                # Deterministic message: sort by label key.
                parts = [
                    f"{key!r} ({old!r} → {new!r})"
                    for key, old, new in sorted(changes, key=lambda t: t[0])
                ]

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            handler_id=handler.id,
                            changes=", ".join(parts),
                        ),
                        content_object=connector,
                        path=handler.file_path,
                    )
                )

        return results

    @staticmethod
    def _label_values(handler: HandlerData) -> dict:
        """Return the values of the guarded labels on this handler.

        Uses the property accessors so `triggering.labels is None`
        collapses to ``{key: None}`` on both keys — mirrors what
        `HandlerData.xsoar_integration_id` / `xsoar_pack_id` return.
        Missing == None, so any transition (None→str, str→None,
        str→different-str) is picked up by the dict comparison.
        """
        return {
            "xsoar-integration-id": handler.xsoar_integration_id,
            "xsoar-pack-id": handler.xsoar_pack_id,
        }

    @classmethod
    def _changed_labels(
        cls, old_handler: HandlerData, new_handler: HandlerData
    ) -> List[Tuple[str, object, object]]:
        """Return ``[(key, old_value, new_value)]`` for guarded labels
        whose value differs between the two snapshots.
        """
        old = cls._label_values(old_handler)
        new = cls._label_values(new_handler)
        changes: List[Tuple[str, object, object]] = []
        for key in _GUARDED_LABELS:
            if old[key] != new[key]:
                changes.append((key, old[key], new[key]))
        return changes
