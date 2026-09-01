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
        "action on its fetch-issues capability."
    )
    rationale = (
        "The classifier is a backend-managed field whose delivered name to the "
        "handler is 'mappingId' (title 'Classifier'). When a handler surfaces "
        "this field - either via a serializer field_mappings entry with "
        "field_name == 'mappingId', or via a config field whose raw id is "
        "'mappingId' with no serializer rename - the platform must be able to "
        "display the instance's configured classifier. The 'show_classifier' "
        "handler action drives that surface, and it lives on the fetch flow "
        "(the fetch-issues capability). A handler that delivers a classifier "
        "field but omits the 'show_classifier' action leaves users unable to "
        "see the classifier the instance is configured with."
    )
    error_message = (
        "Handler '{handler_id}' delivers classifier field(s) {fields} (the "
        "backend '{delivered}' field) but is missing a '{action}' action on "
        "its fetch-issues capability: {reason}."
    )
    related_field = "capabilities[].actions"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """For each XSOAR handler, if the handler delivers a classifier field
        (resolving to the backend ``mappingId`` field, via serializer rename or
        raw config id), require that the handler's fetch-issues capability
        declares a ``show_classifier`` action.

        Handlers with no classifier field are skipped (no-op). A violation is
        only emitted when a classifier field exists but the required action is
        absent (fail closed). One aggregated result per offending handler,
        pathed at the offending ``handler.yaml``.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            # Config field ids declared anywhere on the connector's unified
            # capability configurations. Detection keys purely on the delivered
            # name ``mappingId`` (per the agreed basis), so we only need to know
            # whether a raw config field with that id exists.
            config_field_ids = self._connector_config_field_ids(connector)
            has_raw_mapping_id_config = (
                CLASSIFIER_DELIVERED_FIELD in config_field_ids
            )

            for handler in connector.xsoar_handlers:
                classifier_field_ids = self._classifier_field_ids(
                    handler, has_raw_mapping_id_config
                )
                if not classifier_field_ids:
                    # No classifier field delivered by this handler -> nothing
                    # to enforce.
                    continue

                fetch_cap = self._fetch_issues_capability(handler)
                reason = self._missing_action_reason(fetch_cap)
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
        self, handler: HandlerData, has_raw_mapping_id_config: bool
    ) -> Set[str]:
        """Resolve the set of classifier field ids this handler delivers as
        the backend ``mappingId`` field.

        Detection basis (keyed on the delivered name ``mappingId``):
          (a) serializer field_mappings entry with field_name == "mappingId"
              -> the entry's raw ``id`` (e.g. ``<handler>_mappingId``).
          (b) a config field whose raw id == "mappingId" AND no serializer
              entry renames it -> ``mappingId`` itself is delivered as-is.
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
    def _missing_action_reason(
        fetch_cap: Optional[HandlerCapability],
    ) -> Optional[str]:
        """Return a human-readable reason string if the required action is
        missing, or ``None`` if the fetch-issues capability declares it.
        """
        if fetch_cap is None:
            return "no fetch-issues capability is present on the handler"

        action_types = {a.type for a in fetch_cap.actions if a and a.type}
        if REQUIRED_ACTION in action_types:
            return None

        return (
            f"capability '{fetch_cap.id}' declares "
            f"{sorted(action_types) if action_types else '[]'}"
        )
