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
        "of parameters per handler is derived from "
        "`Connector.visible_fields_for_handler(handler)` — i.e. every raw "
        "field id visible to that handler across ``connection.yaml`` "
        "(general_configurations and the profiles the handler auth-binds "
        "to), ``capabilities.yaml`` (general_configurations), and "
        "``configurations.yaml`` (both parent-capability entries AND "
        "grouped sub-capability entries the pre-walker code silently "
        "dropped)."
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
    # Concrete descriptor of the physical files the walker aggregates from
    # (per plans/handler-visible-fields-walker.md §Section 7 Q6). Points
    # authors at the YAMLs they can edit rather than a runtime concept.
    related_field = "connection.yaml / capabilities.yaml / configurations.yaml"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Per-handler diff of the connector-side raw field ids visible to
        each XSOAR handler.

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

                removed = self._removed_param_ids(
                    old_connector, old_handler, connector, handler
                )
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
    def _param_ids(connector: Connector, handler: HandlerData) -> Set[str]:
        """Return the set of raw connector-side parameter names visible
        to ``handler`` on ``connector`` (as produced by
        :meth:`Connector.visible_fields_for_handler`).
        """
        return {
            vf.raw_id
            for vf in connector.visible_fields_for_handler(handler)
            if vf.raw_id
        }

    def _removed_param_ids(
        self,
        old_connector: Connector,
        old_handler: HandlerData,
        new_connector: Connector,
        new_handler: HandlerData,
    ) -> Set[str]:
        return self._param_ids(old_connector, old_handler) - self._param_ids(
            new_connector, new_handler
        )
