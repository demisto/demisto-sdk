from __future__ import annotations

from typing import Iterable, List, cast

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


class NoChangedHandlerModuleValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO186"
    description = (
        "Breaking-change check: a handler's `metadata.module` must not "
        "change between versions. `metadata.module` names the platform "
        "team that owns the handler and is the primary self-declaring "
        "signal used by `HandlerData.is_xsoar`. Diffs are performed per "
        "`handler.id` on handlers that exist in BOTH the prior and the "
        "new version; newly-added or removed handlers are not this "
        "validator's concern (CO176 covers handler-id removals)."
    )
    rationale = (
        "Changing a handler's module silently rewrites its ownership "
        "classification: an XSOAR handler flipped to a non-xsoar module "
        "vanishes from every XSOAR-only validator (CO155, CO156, CO159 "
        "and every CO validator that iterates `connector.xsoar_handlers`), "
        "so structural regressions ship green. A non-xsoar handler "
        "flipped to `xsoar` is the reverse: it silently opts into the "
        "XSOAR contracts without any of those validators having gated "
        "the edit. Neither schema nor OPA catches either direction, so "
        "this validator is the only guard."
    )
    error_message = (
        "Handler '{handler_id}' has changed `metadata.module` from "
        "{old_module!r} to {new_module!r}. Module identifies the owning "
        "team and must remain stable across versions."
    )
    related_field = "metadata.module"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Per-handler equality diff of `metadata.module`.

        Unlike CO175/CO179 this walks ALL handlers (not just
        `xsoar_handlers`) because the invariant is bidirectional:
        catching a flip TO ``xsoar`` matters as much as catching a flip
        AWAY from it. Handlers absent from one side (added or removed)
        are skipped — CO176's `handler_id` family owns id-set changes.
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

                if not self._module_changed(old_handler, handler):
                    continue

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            handler_id=handler.id,
                            old_module=old_handler.module,
                            new_module=handler.module,
                        ),
                        content_object=connector,
                        path=handler.file_path,
                    )
                )

        return results

    @staticmethod
    def _module_changed(
        old_handler: HandlerData, new_handler: HandlerData
    ) -> bool:
        """True iff `metadata.module` differs between the two snapshots.

        `HandlerData.module` is the property view over
        `metadata.module`; it returns ``None`` when the module key is
        absent, so this comparison naturally treats "unset" as its own
        value. Any transition — set→unset, unset→set, or set→different —
        counts as a change.
        """
        return old_handler.module != new_handler.module
