from __future__ import annotations

from typing import Iterable, List, Set, cast

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


class NoRemovedConnectorParamsValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO175"
    description = (
        "Breaking-change check: no XSOAR-relevant connector parameter that "
        "existed in the prior version of a handler may be removed. The set "
        "of parameters per handler is derived from `handler.resolved_params` "
        "(connection.yaml general_configurations, the profiles this handler "
        "authenticates against, capabilities.yaml general_configurations, "
        "and configurations.yaml entries for this handler's capabilities)."
    )
    rationale = (
        "Removing a parameter that existed in a prior release is a breaking "
        "change: enabled instances relying on that parameter would lose "
        "configuration state and may stop working after upgrade. Parameters "
        "may only be added, deprecated, or renamed (with explicit migration), "
        "never silently deleted."
    )
    error_message = (
        "Handler '{handler_id}' removed parameters that existed in the prior "
        "version: {removed}."
    )
    related_field = "resolved_params"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Per-handler diff of the ``resolved_params`` connector-side names.

        Only XSOAR handlers that exist in BOTH the old and the new version
        are diffed (matched by ``handler.id``). Newly-added handlers cannot
        have "removed" params by definition; handlers that vanished are not
        our concern here (CO176 / other guards cover id-shape breakages).
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            old_connector = cast(ContentTypes, connector.old_base_content_object)
            if old_connector is None:
                continue

            old_by_id = {h.id: h for h in old_connector.xsoar_handlers}

            for handler in connector.xsoar_handlers:
                old_handler = old_by_id.get(handler.id)
                if old_handler is None:
                    continue  # newly-added handler

                removed = self._removed_param_ids(old_handler, handler)
                if not removed:
                    continue

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            handler_id=handler.id,
                            removed=", ".join(map(repr, sorted(removed))),
                        ),
                        content_object=connector,
                        path=handler.file_path,
                    )
                )

        return results

    @staticmethod
    def _param_ids(handler: HandlerData) -> Set[str]:
        """Return the set of connector-side parameter names visible to
        `handler` (as resolved by the parser)."""
        return {
            rp.connector_param_name
            for rp in (handler.resolved_params or [])
            if rp and rp.connector_param_name
        }

    def _removed_param_ids(
        self, old_handler: HandlerData, new_handler: HandlerData
    ) -> Set[str]:
        return self._param_ids(old_handler) - self._param_ids(new_handler)
