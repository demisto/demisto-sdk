"""CO130 - ``fetch-issues`` capability must be wired end-to-end.

Every XSOAR handler subscribing to the ``fetch-issues`` capability
must satisfy two independent requirements:

1. **Serializer**: ``serializer.yaml`` emits ``isFetch: true`` via
   ``computed_fields``, gated by a capability condition matching the
   subscribed cap id with ``value == "on"``. The XSOAR backend uses
   this flag to schedule the recurring fetch job.

2. **Configurations**: the capability's ``configurations[]`` entry
   declares four required fields with the correct field-shape so
   instance creation succeeds: ``incidentType`` (select, dynamicField
   ``incident-type``), ``incidentFetchInterval`` (duration),
   ``incomingMapperId`` (select, ``mapper-incoming``), ``mappingId``
   (select, ``classifier``).

Serializer defects are keyed to ``<handler>/serializer.yaml`` (per-
handler ignore chain); configurations defects are keyed to
``configurations.yaml`` (connector-scoped — the entry is shared
across handlers subscribing to the same cap id).
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
)
from demisto_sdk.commands.content_graph.objects.connector_handler_view import (
    FieldOrigin,
    HandlerVisibleField,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

FETCH_ISSUES_CAPABILITY = "fetch-issues"
FETCH_ISSUES_FLAG = "isFetch"

# (field_id, expected_field_type, expected_dynamicField-or-None).
# ``None`` means the field is not a dynamic-values select
# (``incidentFetchInterval`` is a duration).
FETCH_ISSUES_REQUIRED_FIELDS: List[tuple] = [
    ("incidentType", "select", "incident-type"),
    ("incidentFetchInterval", "duration", None),
    ("incomingMapperId", "select", "mapper-incoming"),
    ("mappingId", "select", "classifier"),
]


class IsValidFetchValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO130"
    description = (
        "Validates that every XSOAR handler subscribing to the "
        "`fetch-issues` capability (a) emits the `isFetch: true` "
        "backend flag via its serializer.yaml `computed_fields`, and "
        "(b) has the required fetch-issues configuration fields "
        "(incidentType, incidentFetchInterval, incomingMapperId, "
        "mappingId) declared under the capability's configurations "
        "entry with the correct field_type and dynamicField."
    )
    rationale = (
        "The XSOAR BE is capability-agnostic - it still needs the "
        "legacy `isFetch: true` flag to schedule the recurring fetch "
        "job. In UCP the `isFetch` checkbox is removed (choosing the "
        "capability IS the opt-in), so the flag must be emitted via "
        "serializer `computed_fields`. Additionally the capability's "
        "configurations must expose the mandatory fetch-issues fields "
        "(interval, incident type, incoming mapper, classifier) with "
        "the correct field_type/dynamic-values shape so instance "
        "creation succeeds."
    )
    error_message = (
        "Connector '{connector_id}' has XSOAR handler(s) subscribing "
        "to the 'fetch-issues' capability but the fetch-issues wiring "
        "is incomplete: {issues}"
    )
    related_field = "configurations"
    is_auto_fixable = False
    # ``related_file_type`` feeds TWO independent ignore chains and each
    # needs its own entry (mirrors CO171/CO172):
    #
    #   1. ``ConnectorsValidator.should_run`` -> ``is_error_ignored`` ->
    #      ``_resolve_ignore_file_keys``: preflight expansion into
    #      ``.connector-ignore`` section keys. Without CONNECTOR_SERIALIZER,
    #      ``[file:<handler>/serializer.yaml]`` entries are never consulted
    #      and the validator runs even when every handler explicitly opts
    #      out.
    #   2. ``ValidateManager.filter_validation_results`` ->
    #      ``_is_connector_handler_validation``: post-hoc per-result filter
    #      triggered when EITHER CONNECTOR_HANDLER OR CONNECTOR_SERIALIZER
    #      is present.
    #
    # CONNECTOR_CONFIGURATIONS keeps Part-2 results discoverable under
    # ``[file:configurations.yaml]`` in chain 1.
    related_file_type = [
        RelatedFileType.CONNECTOR_CONFIGURATIONS,
        RelatedFileType.CONNECTOR_HANDLER,
        RelatedFileType.CONNECTOR_SERIALIZER,
    ]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for connector in content_items:
            results.extend(self._collect_serializer_results(connector))
            results.extend(self._collect_configurations_results(connector))
        return results

    def _collect_serializer_results(
        self, connector: Connector
    ) -> List[ValidationResult]:
        """One result per handler whose serializer.yaml is missing the
        ``isFetch: true`` computed_fields rule for one of its
        fetch-issues* cap ids. Keyed to ``<handler>/serializer.yaml``
        for per-handler ignore routing."""
        results: List[ValidationResult] = []
        for handler in connector.xsoar_handlers:
            per_handler_issues: List[str] = []
            for cap_id in handler.capability_ids_matching(FETCH_ISSUES_CAPABILITY):
                if not handler.serializer_emits_capability_flag(
                    FETCH_ISSUES_FLAG, cap_id
                ):
                    per_handler_issues.append(
                        f"handler '{handler.id}' subscribes to "
                        f"capability '{cap_id}' but its serializer.yaml "
                        f"does not emit `computed_fields` output "
                        f"'{FETCH_ISSUES_FLAG}: true' under a capability "
                        f"condition '{cap_id} == on'"
                    )
            if not per_handler_issues:
                continue
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        issues="; ".join(per_handler_issues),
                    ),
                    content_object=connector,
                    path=handler.serializer_path,
                )
            )
        return results

    def _collect_configurations_results(
        self, connector: Connector
    ) -> List[ValidationResult]:
        """One result per unique fetch-issues* cap id whose
        configurations wiring is broken. Deduplicated across handlers
        sharing a cap id (they share the entry). First subscribing
        handler drives the walker visibility check."""
        results: List[ValidationResult] = []
        seen_capability_ids: Dict[str, HandlerData] = {}
        for handler in connector.xsoar_handlers:
            for cap_id in handler.capability_ids_matching(FETCH_ISSUES_CAPABILITY):
                if cap_id not in seen_capability_ids:
                    seen_capability_ids[cap_id] = handler

        for cap_id, handler in seen_capability_ids.items():
            capability_issues = self._check_capability_fields(
                connector, handler, cap_id
            )
            if not capability_issues:
                continue
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        issues="; ".join(capability_issues),
                    ),
                    content_object=connector,
                    path=connector.configurations_file.file_path,
                )
            )
        return results

    def _check_capability_fields(
        self,
        connector: Connector,
        handler: HandlerData,
        capability_id: str,
    ) -> List[str]:
        """Configurations-half checks for one (handler, cap_id) pair.

        Two-tier error path: if the walker sees NO fields for
        ``capability_id`` at all (missing entry or missing file),
        emit a single "no configurations[] entry" issue. Otherwise
        emit one issue per required-field defect (missing / wrong
        field_type / wrong dynamicField) so authors see exactly which
        of the four fields drifted.
        """
        # Index by runtime name (post-serializer) so grouped connectors
        # that authored namespaced ids and renamed them back via
        # field_mappings are matched correctly.
        fields_by_runtime_id: Dict[str, HandlerVisibleField] = {
            vf.runtime_name: vf
            for vf in connector.visible_fields_for_handler_by_origin(
                handler, FieldOrigin.CONFIGURATIONS_CAPABILITY
            )
            if vf.capability_id == capability_id
        }

        if not fields_by_runtime_id:
            return [
                f"configurations.yaml has no `configurations[]` entry "
                f"with id '{capability_id}' - the fetch-issues capability "
                f"must have its own configurations entry containing the "
                f"required fields"
            ]

        issues: List[str] = []
        for expected_id, expected_type, expected_dyn in FETCH_ISSUES_REQUIRED_FIELDS:
            vf = fields_by_runtime_id.get(expected_id)
            if vf is None:
                issues.append(
                    f"capability '{capability_id}' is missing required "
                    f"field '{expected_id}'"
                )
                continue

            actual_type = vf.field.field_type
            if actual_type != expected_type:
                issues.append(
                    f"capability '{capability_id}' field '{expected_id}' "
                    f"has field_type='{actual_type}' but must be "
                    f"'{expected_type}'"
                )

            if expected_dyn is not None:
                actual_dyn = vf.dynamic_field_name
                if actual_dyn != expected_dyn:
                    issues.append(
                        f"capability '{capability_id}' field "
                        f"'{expected_id}' has "
                        f"metadata.dynamic_values.params.dynamicField="
                        f"'{actual_dyn}' but must be '{expected_dyn}'"
                    )

        return issues
