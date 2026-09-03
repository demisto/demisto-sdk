from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.initializer import ConnectorAwareInitializer
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsIntegrationCoveredByConnectorValidator(BaseValidator[ContentTypes]):
    """CO192 -- integration-side coverage guard (inverse of CO164).

    Every integration that is in scope for the connector flow -- i.e. on the
    PLATFORM marketplace, not deprecated, and whose support level is NOT one
    of ``{partner, community}`` -- MUST be referenced by at least one
    connector's XSOAR handler via ``triggering.labels.xsoar-integration-id``.

    An in-scope integration with no backing handler is a coverage gap:
    UCP cannot instantiate it, so it is content that cannot be reached.

    Implementation note -- why this validator does not read ``content_items``:

    ``ConnectorAwareInitializer`` already computes exactly the "uncovered"
    set as a byproduct of the cross-match phases in
    ``gather_objects_to_run_on``, then drops those integrations from the
    validation set (see ``_remove_unmatched_integrations``). By the time
    ``obtain_invalid_content_items`` runs, the offenders are no longer in
    ``content_items`` -- iterating it would always find zero violations.

    Instead, the initializer stashes the uncovered set on a class-level
    slot and exposes it via
    ``ConnectorAwareInitializer.get_integrations_without_connector_handler``.
    Reading the getter costs nothing beyond returning the frozen set;
    there is no extra graph query. When the connector flow did not run
    (``--run-connectors-validation`` was not passed) the getter returns
    ``frozenset()`` and this validator emits nothing -- which is the
    correct behaviour: no scan means no verdict.
    """

    error_code = "CO192"
    description = (
        "Every in-scope integration (PLATFORM marketplace, not deprecated, "
        "support level not in {partner, community}) MUST be referenced by "
        "at least one connector's XSOAR handler via "
        "triggering.labels.xsoar-integration-id."
    )
    rationale = (
        "The inverse of CO164 (connector -> integration). An in-scope "
        "integration with no backing connector handler cannot be "
        "instantiated through UCP: it is content that customers cannot "
        "reach. Flagging it here forces the coverage gap to be closed "
        "(add a handler that pins this integration's YML id) or the "
        "integration's scope to be narrowed (deprecate it, mark it "
        "partner/community, or drop PLATFORM from its marketplaces)."
    )
    error_message = (
        "Integration '{integration_id}' is in scope for the connector flow "
        "(PLATFORM marketplace, not deprecated, support level not in "
        "{{partner, community}}) but no connector's XSOAR handler "
        "references it via 'triggering.labels.xsoar-integration-id'. "
        "Add a handler that pins this integration's YML id, or narrow the "
        "integration's scope so the connector flow no longer considers it."
    )
    related_field = "commonfields.id"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        # See the class docstring for why ``content_items`` is not read.
        uncovered = (
            ConnectorAwareInitializer.get_integrations_without_connector_handler()
        )
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    integration_id=integration.object_id,
                ),
                content_object=integration,
            )
            for integration in uncovered
        ]
