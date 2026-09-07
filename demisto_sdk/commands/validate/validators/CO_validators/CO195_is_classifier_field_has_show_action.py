from __future__ import annotations

from typing import Iterable, List, Optional, Set

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerCapability,
    HandlerData,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

# The backend-managed field name delivered to the handler for the instance's
# configured incident classifier. A connector's serializer.yaml may rename a
# raw config field id to this delivered name via a field_mappings entry
# ({id: <raw>, field_name: mappingId}); alternatively a config field may
# already carry the raw id "mappingId" (no serializer rename).
CLASSIFIER_DELIVERED_FIELD = "mappingId"

# The fetch capability that owns the classifier flow. A handler that surfaces
# the classifier field must expose it on its fetch-issues capability.
FETCH_ISSUES_BASE_CAP = "fetch-issues"

# The action a fetch-issues capability must declare when the handler delivers
# a classifier field.
REQUIRED_ACTION = "show_classifier"

# A conforming ``show_classifier`` action must reference EXACTLY ONE classifier
# field via its ``return_data`` (the single classifier field it surfaces).
EXPECTED_RETURN_DATA_COUNT = 1

# Metadata markers that identify a backend-managed classifier config field.
# A config field is a classifier field when its metadata carries the xsoar
# dynamic-values hook ``dynamicField == "classifier"`` and is flagged as a
# backend-owned config field (``xsoar.config_type == "backend"``). Backend
# dynamic fields may be filtered out of the parsed config field list, so this
# metadata inspection is the robust way to detect them.
CLASSIFIER_DYNAMIC_FIELD = "classifier"
BACKEND_CONFIG_TYPE = "backend"


def _capability_base_id(cap_id: str) -> str:
    """Strip the ``_<suffix>`` from a namespaced capability id.

    Grouped connectors namespace capability ids as ``<base>_<integration>``
    (e.g. ``fetch-issues_akamai-waf-siem``). Standard non-grouped connectors
    use the bare base id (e.g. ``fetch-issues``). This helper returns the base
    portion in both cases (mirrors CO161's helper).
    """
    return cap_id.split("_", 1)[0] if cap_id else ""


class IsClassifierFieldHasShowActionValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO195"
    description = (
        "Validates that every handler which delivers a classifier field "
        "(the backend-managed 'mappingId' field) declares a 'show_classifier' "
        "action on its fetch-issues capability AND that the action is properly "
        "formatted: its return_data references the delivered classifier field "
        "id and contains EXACTLY ONE entry."
    )
    rationale = (
        "The classifier is a backend-managed field whose delivered name to the "
        "handler is 'mappingId' (title 'Classifier'). A handler surfaces this "
        "field when: (a) its serializer field_mappings renames a raw id to "
        "field_name == 'mappingId' (the raw id may be prefixed, e.g. "
        "'<handler>_mappingId'); (b) a config field's delivered id is "
        "'mappingId'; or (c) a config field's metadata marks it as the backend "
        "classifier (metadata.dynamic_values.params.dynamicField == "
        "'classifier' with metadata.xsoar.config_type == 'backend'). When a "
        "handler delivers such a field, the platform must be able to display "
        "the instance's configured classifier. The 'show_classifier' handler "
        "action drives that surface and lives on the fetch flow (the "
        "fetch-issues capability), and its 'return_data' must reference the "
        "OWN classifier field id(s) the handler delivers so the action points "
        "at the right field AND must contain exactly one entry (an empty "
        "return_data points at nothing, while two or more entries are "
        "ambiguous about which field the action displays). A handler that "
        "delivers a classifier field but omits the action - or declares it "
        "with return_data that does not include the delivered classifier id, "
        "or that does not name exactly one classifier field - leaves users "
        "unable to see the classifier the instance is configured with."
    )
    error_message = (
        "Handler '{handler_id}' delivers classifier field(s) {fields} (the "
        "backend '{delivered}' field) but its '{action}' action on the "
        "fetch-issues capability is invalid: {reason}."
    )
    related_field = "capabilities[].actions"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """For each XSOAR handler, if the handler delivers a classifier field
        (resolving to the backend ``mappingId`` field via serializer rename,
        raw config id, or backend classifier metadata), require that the
        handler's fetch-issues capability declares a properly-formatted
        ``show_classifier`` action: it must exist, its ``return_data`` must
        reference the delivered classifier field id(s), AND its ``return_data``
        must contain exactly one entry.

        Handlers with no classifier field are skipped (no-op). A violation is
        emitted when a classifier field exists but the required action is
        absent, OR when the action is present but its ``return_data`` does not
        include the delivered classifier id(s), OR its ``return_data`` does not
        contain exactly one entry (fail closed). One aggregated result per
        offending handler, pathed at the offending ``handler.yaml``.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            # Raw config field ids whose delivered name is ``mappingId`` (a
            # config field carrying that raw id directly), plus config field
            # ids whose metadata marks them as the backend classifier field.
            config_field_ids = self._connector_config_field_ids(connector)
            has_raw_mapping_id_config = CLASSIFIER_DELIVERED_FIELD in config_field_ids
            metadata_classifier_ids = self._metadata_classifier_field_ids(connector)

            for handler in connector.xsoar_handlers:
                classifier_field_ids = self._classifier_field_ids(
                    handler,
                    has_raw_mapping_id_config,
                    metadata_classifier_ids,
                )
                if not classifier_field_ids:
                    # No classifier field delivered by this handler -> nothing
                    # to enforce.
                    continue

                fetch_cap = self._fetch_issues_capability(handler)
                reason = self._action_problem_reason(fetch_cap, classifier_field_ids)
                if reason is None:
                    continue

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            handler_id=handler.id,
                            fields=sorted(classifier_field_ids),
                            delivered=CLASSIFIER_DELIVERED_FIELD,
                            action=REQUIRED_ACTION,
                            reason=reason,
                        ),
                        content_object=connector,
                        path=handler.file_path,
                    )
                )

        return results

    @staticmethod
    def _connector_config_field_ids(connector: ContentTypes) -> Set[str]:
        """Collect all raw config field ids declared across the connector's
        unified capability configurations (general + per-capability).
        """
        field_ids: Set[str] = set()
        for cap in connector.capabilities:
            for group in cap.configurations:
                for field in group.fields:
                    if field and field.id:
                        field_ids.add(field.id)
        return field_ids

    @staticmethod
    def _is_classifier_metadata(metadata: Optional[dict]) -> bool:
        """Return True if a config field's ``metadata`` dict marks it as the
        backend-managed classifier field.

        Basis (both must hold):
          - metadata.dynamic_values.params.dynamicField == "classifier"
          - metadata.xsoar.config_type == "backend"
        Defensive against missing/mis-typed nested keys (metadata is a
        free-form dict).
        """
        if not isinstance(metadata, dict):
            return False

        dynamic_values = metadata.get("dynamic_values")
        params = (
            dynamic_values.get("params") if isinstance(dynamic_values, dict) else None
        )
        dynamic_field = params.get("dynamicField") if isinstance(params, dict) else None
        if dynamic_field != CLASSIFIER_DYNAMIC_FIELD:
            return False

        xsoar = metadata.get("xsoar")
        config_type = xsoar.get("config_type") if isinstance(xsoar, dict) else None
        return config_type == BACKEND_CONFIG_TYPE

    def _metadata_classifier_field_ids(self, connector: ContentTypes) -> Set[str]:
        """Collect config field ids whose metadata marks them as the
        backend-managed classifier field (across all unified capability
        configurations). For strict connectors this id is ``mappingId``.
        """
        classifier_ids: Set[str] = set()
        for cap in connector.capabilities:
            for group in cap.configurations:
                for field in group.fields:
                    if (
                        field
                        and field.id
                        and self._is_classifier_metadata(field.metadata)
                    ):
                        classifier_ids.add(field.id)
        return classifier_ids

    @staticmethod
    def _serializer_rename_source_ids(handler: HandlerData) -> Set[str]:
        """Raw ids that the handler's serializer renames to ``mappingId``
        (field_mappings entries with field_name == "mappingId").
        """
        source_ids: Set[str] = set()
        serializer = handler.serializer
        if serializer:
            for fm in serializer.field_mappings:
                if fm and fm.field_name == CLASSIFIER_DELIVERED_FIELD and fm.id:
                    source_ids.add(fm.id)
        return source_ids

    def _classifier_field_ids(
        self,
        handler: HandlerData,
        has_raw_mapping_id_config: bool,
        metadata_classifier_ids: Set[str],
    ) -> Set[str]:
        """Resolve the set of classifier field ids this handler delivers as
        the backend ``mappingId`` field.

        Detection basis (union of the following):
          (a) serializer field_mappings entry with field_name == "mappingId"
              -> the entry's raw ``id`` (e.g. ``<handler>_mappingId``).
          (b) a config field whose raw id == "mappingId" AND no serializer
              entry renames it -> ``mappingId`` itself is delivered as-is.
          (c) a config field whose metadata marks it as the backend classifier
              (dynamicField == "classifier" + config_type == "backend") -> its
              raw id (``mappingId`` for strict connectors). Covers backend
              dynamic fields that are filtered from the parsed config list.
        """
        classifier_ids = self._serializer_rename_source_ids(handler)

        if has_raw_mapping_id_config:
            # Only treat the raw "mappingId" config field as delivered as-is
            # when the serializer does NOT rename that same id to something
            # else. (If a serializer entry has id == "mappingId" the raw field
            # is being remapped and is handled by case (a) semantics.)
            serializer = handler.serializer
            renamed_ids = (
                {
                    fm.id
                    for fm in serializer.field_mappings
                    if fm and fm.id and fm.field_name
                }
                if serializer
                else set()
            )
            if CLASSIFIER_DELIVERED_FIELD not in renamed_ids:
                classifier_ids.add(CLASSIFIER_DELIVERED_FIELD)

        # Metadata-detected backend classifier field ids always count as
        # delivered (they are the strict-connector case, id == "mappingId").
        classifier_ids |= metadata_classifier_ids

        return classifier_ids

    @staticmethod
    def _fetch_issues_capability(
        handler: HandlerData,
    ) -> Optional[HandlerCapability]:
        """Return the handler's fetch-issues capability (base id match), or
        ``None`` if the handler subscribes to no fetch-issues capability.
        """
        for cap in handler.capabilities:
            if _capability_base_id(cap.id) == FETCH_ISSUES_BASE_CAP:
                return cap
        return None

    @staticmethod
    def _action_problem_reason(
        fetch_cap: Optional[HandlerCapability],
        classifier_field_ids: Set[str],
    ) -> Optional[str]:
        """Return a human-readable reason string if the show_classifier action
        is missing OR improperly formatted, or ``None`` if the fetch-issues
        capability declares a conforming action.

        A conforming ``show_classifier`` action must (both):
          - reference every delivered classifier field id via its
            ``return_data``; and
          - declare EXACTLY ONE ``return_data`` entry (an empty return_data
            points at nothing, while two or more entries are ambiguous about
            which field the action displays).
        """
        if fetch_cap is None:
            return "no fetch-issues capability is present on the handler"

        show_actions = [a for a in fetch_cap.actions if a and a.type == REQUIRED_ACTION]
        if not show_actions:
            action_types = {a.type for a in fetch_cap.actions if a and a.type}
            return (
                f"the required '{REQUIRED_ACTION}' action is missing "
                f"(capability '{fetch_cap.id}' declares "
                f"{sorted(action_types) if action_types else '[]'})"
            )

        # The action is present - verify at least one show_classifier action is
        # properly formatted: its return_data references EVERY delivered
        # classifier field id AND contains exactly one entry. (A handler
        # delivers a single classifier id in practice; requiring the superset
        # guards against a mismatch where the action points elsewhere, and the
        # cardinality check keeps the classifier surface unambiguous.)
        for action in show_actions:
            return_data = action.return_data or []
            if (
                classifier_field_ids.issubset(set(return_data))
                and len(return_data) == EXPECTED_RETURN_DATA_COUNT
            ):
                return None

        # No show_classifier action is properly formatted. Report whether the
        # problem is a missing/mismatched id, a bad cardinality, or both.
        observed = sorted(
            {rd for action in show_actions for rd in (action.return_data or [])}
        )
        references_ids = any(
            classifier_field_ids.issubset(set(action.return_data or []))
            for action in show_actions
        )
        if not references_ids:
            return (
                f"the '{REQUIRED_ACTION}' action's return_data does not "
                f"reference the delivered classifier field id(s) "
                f"{sorted(classifier_field_ids)}; return_data contains "
                f"{observed if observed else '[]'}"
            )
        # The id is referenced but no conforming action has exactly one entry.
        counts = sorted(len(action.return_data or []) for action in show_actions)
        return (
            f"the '{REQUIRED_ACTION}' action's return_data must contain exactly "
            f"one classifier field entry, but found {counts} "
            f"(return_data contains {observed if observed else '[]'})"
        )
