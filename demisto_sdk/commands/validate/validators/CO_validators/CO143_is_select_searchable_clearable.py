"""CO143 - IsSelectSearchableClearableValidator.

Every ``select`` / ``multi_select`` field exposed to XSOAR handlers MUST:

1. Set ``options.clearable: true`` unconditionally. The user must
   always be able to un-pick a picked value.
2. Set ``options.searchable: true`` when the field's
   ``options.values`` contains **more than 5** items OR when the
   field's values are resolved dynamically at runtime (via
   ``metadata.dynamic_values.params.dynamicField``). Dynamic-value
   fields have no authoring-time count, so we conservatively assume
   "may exceed 5" and require ``searchable: true``.

Static enumerations with ≤5 items are the only case where
``searchable`` may be omitted — those are ergonomic to scan
directly.

We consume the unified handler-visible-fields walker
(:meth:`Connector.visible_fields_for_handler`) which already covers
every physical location a select field can hide: ``connection.yaml``
general + profiles bound to the handler, ``capabilities.yaml``
general, and ``configurations.yaml`` general + per-capability
entries (including grouped sub-cap ids the parser silently drops
from ``self.capabilities``). The walker also applies the
``serializer.yaml`` ``field_mappings`` rename per field so
grouped-connector namespaced ids report as the runtime name the
integration actually sees.

Structural shape inspection uses the walker's convenience
accessors — :attr:`HandlerVisibleField.field_type` for the
``select`` / ``multi_select`` filter, :attr:`HandlerVisibleField.options`
for the ``clearable`` / ``searchable`` / ``values`` reads, and
:attr:`HandlerVisibleField.dynamic_field_name` for the dynamic-values
detection (schema-canonical ``metadata.dynamic_values.params.dynamicField``
shape).

Per-finding granularity: one ``ValidationResult`` per
(handler, runtime_name, defect) where ``defect`` ∈ {``clearable``,
``searchable``}. Dedupe key = (runtime_name, defect) per handler so
the same field appearing in multiple source files fires once for
each defect. Walker order (CONNECTION_GENERAL → CONNECTION_PROFILE
→ CAPABILITIES_GENERAL → CONFIGURATIONS_GENERAL →
CONFIGURATIONS_CAPABILITY) determines which occurrence wins the
error-message location.

Non-XSOAR handlers are skipped (mirrors CO141 / CO145 policy).
"""

from __future__ import annotations

from typing import Any, Iterable, List, Set, Tuple

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
)
from demisto_sdk.commands.content_graph.objects.connector_handler_view import (
    HandlerVisibleField,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

# Field types that participate in CO143. Anything else is skipped.
SELECT_FIELD_TYPES = frozenset({"select", "multi_select"})

# Static-values threshold above which searchable is required. Dynamic
# values are treated as "may exceed this" (count unknown at authoring
# time) and always require searchable too.
SEARCHABLE_MIN_ITEMS = 5


class IsSelectSearchableClearableValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO143"
    description = (
        "Every `select` / `multi_select` field visible to XSOAR "
        "handlers must set `options.clearable: true` unconditionally "
        "and `options.searchable: true` when `options.values` has "
        "more than 5 items or when values are resolved dynamically "
        "(`metadata.dynamic_values.params.dynamicField`) — dynamic "
        "values have unknown authoring-time count, so we "
        "conservatively assume they exceed the threshold."
    )
    rationale = (
        "The `clearable` flag guarantees the user can always un-pick "
        "a value; without it, once a value is selected the picker "
        "traps the user in that choice. The `searchable` flag only "
        "adds value when the picker has enough options to warrant a "
        "search box — small enumerations (≤5 static items) are "
        "ergonomic to scan directly. Dynamic-value fields resolve "
        "their options at runtime with no upper bound, so we treat "
        "them as always-searchable to protect the UX. Enforcing "
        "both invariants keeps the configuration UI predictable "
        "across every connector."
    )
    error_message = (
        "Connector '{connector_id}' handler '{handler_id}': select "
        "field '{field_id}' in '{source_file}' ({location_hint}) is "
        "missing required 'options.{defect}: true' "
        "(values_count={values_count}). Add "
        "'options.{defect}: true'."
    )
    related_field = "configurations"
    is_auto_fixable = False
    # A finding may originate from any of the three YAML files, so
    # listing all three keeps the per-file ``.connector-ignore``
    # preflight resolution able to short-circuit whichever
    # per-source-file suppression the author wrote.
    related_file_type = [
        RelatedFileType.CONNECTOR_CONNECTION,
        RelatedFileType.CONNECTOR_CAPABILITIES,
        RelatedFileType.CONNECTOR_CONFIGURATIONS,
    ]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.xsoar_handlers:
                results.extend(self._check_handler(connector, handler))

        return results

    # ------------------------------------------------------------------
    # CO143-specific helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _values_count(options: Any) -> int:
        """Return the item count of ``options.values``. Dicts count by
        top-level keys, lists count by length, anything else = 0."""
        values = options.get("values") if isinstance(options, dict) else None
        if isinstance(values, dict):
            return len(values)
        if isinstance(values, list):
            return len(values)
        return 0

    @staticmethod
    def _flag_true(options: Any, key: str) -> bool:
        """True iff ``options[key]`` is exactly ``True``."""
        if not isinstance(options, dict):
            return False
        return options.get(key) is True

    def _check_handler(
        self,
        connector: Connector,
        handler: HandlerData,
    ) -> List[ValidationResult]:
        """Emit one ``ValidationResult`` per (handler, runtime_name,
        defect) finding. Deduplicated per handler.

        Walker order (CONNECTION_GENERAL → CONNECTION_PROFILE →
        CAPABILITIES_GENERAL → CONFIGURATIONS_GENERAL →
        CONFIGURATIONS_CAPABILITY) determines which occurrence of a
        given runtime name lands the error-message location; subsequent
        occurrences of the same (runtime_name, defect) pair are
        suppressed.
        """
        results: List[ValidationResult] = []
        seen: Set[Tuple[str, str]] = set()

        for vf in connector.visible_fields_for_handler(handler):
            if vf.field_type not in SELECT_FIELD_TYPES:
                continue

            runtime_name = vf.runtime_name
            options = vf.options
            is_dynamic = vf.dynamic_field_name is not None
            values_count = self._values_count(options)
            # Message hint - "dynamic" for dynamic-values fields so
            # authors understand why searchable is required despite
            # no static values list.
            values_count_str = "dynamic" if is_dynamic else str(values_count)

            # Defect 1: clearable is always required.
            if not self._flag_true(options, "clearable"):
                key = (runtime_name, "clearable")
                if key not in seen:
                    seen.add(key)
                    results.append(
                        self._build_result(
                            connector=connector,
                            handler=handler,
                            runtime_name=runtime_name,
                            vf=vf,
                            defect="clearable",
                            values_count_str=values_count_str,
                        )
                    )

            # Defect 2: searchable required when values may exceed the
            # threshold. Dynamic-value fields always qualify (count
            # unknown); static fields qualify only when >5 items.
            searchable_required = is_dynamic or values_count > SEARCHABLE_MIN_ITEMS
            if searchable_required and not self._flag_true(options, "searchable"):
                key = (runtime_name, "searchable")
                if key not in seen:
                    seen.add(key)
                    results.append(
                        self._build_result(
                            connector=connector,
                            handler=handler,
                            runtime_name=runtime_name,
                            vf=vf,
                            defect="searchable",
                            values_count_str=values_count_str,
                        )
                    )

        return results

    def _build_result(
        self,
        connector: Connector,
        handler: HandlerData,
        runtime_name: str,
        vf: HandlerVisibleField,
        defect: str,
        values_count_str: str,
    ) -> ValidationResult:
        return ValidationResult(
            validator=self,
            message=self.error_message.format(
                connector_id=connector.object_id,
                handler_id=handler.id,
                field_id=runtime_name,
                source_file=vf.origin.file_label,
                location_hint=vf.location_hint,
                defect=defect,
                values_count=values_count_str,
            ),
            content_object=connector,
            path=vf.source_file,
        )
