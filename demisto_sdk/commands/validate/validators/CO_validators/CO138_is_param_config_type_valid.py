"""CO138 - IsParamConfigTypeValidValidator.

Only a small **whitelist** of
platform-canonical params may carry the
``metadata.xsoar.config_type: "backend"`` marker. Every OTHER
user-visible field in the connector's XSOAR-visible surface MUST
NOT set ``config_type: backend``.

The whitelist (6 canonical field ids):

- ``engine``
- ``engineGroup``
- ``mappingId`` (fetch-issues classifier)
- ``incomingMapperId`` (fetch-issues incoming mapper)
- ``defaultIgnore`` (automation-and-remediation)
- ``integrationLogLevel``

``outgoingMapperId`` is intentionally excluded because mirroring is not supported on platform. See CO141

Two-directional check (per handler):

1. **Whitelist-side:** For each whitelisted field that IS present
   in the XSOAR-visible surface (matched by RUNTIME name, so
   namespaced ids like ``xsoar-akamai_engine``
   matched via ``serializer.yaml`` ``field_mappings`` rename to
   ``engine``), assert ``metadata.xsoar.config_type == "backend"``.
   A whitelisted field without the marker is a violation.

2. **Anti-whitelist side:** For every OTHER field with
   ``metadata.xsoar.config_type == "backend"``, flag it - the
   marker is reserved for the 6 canonical ids only.

Non-XSOAR handlers are skipped.

Per-finding granularity: one ``ValidationResult`` per
(handler, field, defect). Deduplicated by (runtime_name, defect)
per handler.
"""

from __future__ import annotations

from typing import FrozenSet, Iterable, List, Optional, Set, Tuple

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

# ============================================================
# CO138 constants
# ============================================================

# The 6 field ids that MAY carry ``metadata.xsoar.config_type:
# "backend"``. All matches use the post-serializer RUNTIME name.
#
# ``outgoingMapperId`` is intentionally NOT included - CO141 
# forbids it as a user-visible field on Platform. If it does
# appear, CO141 will flag it.
WHITELISTED_BACKEND_PARAMS: FrozenSet[str] = frozenset(
    {
        "engine",
        "engineGroup",
        "mappingId",
        "incomingMapperId",
        "defaultIgnore",
        "integrationLogLevel",
    }
)

# The literal string the BE contract expects.
BACKEND_CONFIG_TYPE = "backend"

# Defect kinds used to dedupe per-handler findings.
_DEFECT_MISSING_BACKEND = "missing_backend"
_DEFECT_UNEXPECTED_BACKEND = "unexpected_backend"


# ============================================================
# CO138 validator
# ============================================================
class IsParamConfigTypeValidValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO138"
    description = (
        'Validates that the `metadata.xsoar.config_type: "backend"` '
        "marker is set on EXACTLY the 6 whitelisted canonical field "
        "ids (engine, engineGroup, mappingId, incomingMapperId, "
        "defaultIgnore, integrationLogLevel) and on no other field. "
        "Matched by post-serializer runtime name."
    )
    rationale = (
        "The `config_type: backend` marker tells the BE this field's "
        "value is consumed by XSOAR's BE (not the integration directly), "
        "which drives the XSOAR BE not to send it to demisto.params."
        "Marking a non-canonical field as backend causes "
        "silent parameter drop; And the integration wont get it in demisto.params"
    )
    error_message = (
        "Connector '{connector_id}' handler '{handler_id}': "
        "field '{field_id}' in '{source_file}'{location_hint} "
        "{problem}."
    )
    related_field = "field.metadata.xsoar.config_type"
    is_auto_fixable = False
    # Same rationale as CO145 / CO141: a finding may originate from
    # any of the three YAML files, so listing all three keeps the
    # per-file ignore preflight able to short-circuit.
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
    # Per-handler two-directional check.
    #
    # The unified walker handles visibility scoping (view_group /
    # required_for_capabilities), per-handler serializer renames, and
    # grouped-connector sub-cap entry matching. We only need to filter
    # on runtime_name + inspect ``metadata.xsoar.config_type`` on each
    # returned field.
    # ------------------------------------------------------------------

    def _check_handler(
        self,
        connector: Connector,
        handler: HandlerData,
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        # Dedupe key = (runtime_name, defect). A field appearing in
        # two source files with the same defect (unlikely but possible
        # via profile+general duplication) only fires once per
        # handler.
        seen: Set[Tuple[str, str]] = set()

        for vf in connector.visible_fields_for_handler(handler):
            runtime_name = vf.runtime_name
            field_config_type = vf.xsoar_config_type
            is_backend = field_config_type == BACKEND_CONFIG_TYPE
            is_whitelisted = runtime_name in WHITELISTED_BACKEND_PARAMS

            defect: Optional[str] = None
            problem: Optional[str] = None
            if is_whitelisted and not is_backend:
                defect = _DEFECT_MISSING_BACKEND
                if field_config_type is None:
                    problem = (
                        f"is missing `metadata.xsoar.config_type: "
                        f'"{BACKEND_CONFIG_TYPE}"` - this canonical '
                        f"field is BE-managed and MUST carry the "
                        f"backend marker"
                    )
                else:
                    problem = (
                        f"has `metadata.xsoar.config_type: "
                        f'"{field_config_type}"` - canonical field MUST be '
                        f'`"{BACKEND_CONFIG_TYPE}"`'
                    )
            elif not is_whitelisted and is_backend:
                defect = _DEFECT_UNEXPECTED_BACKEND
                problem = (
                    f"has `metadata.xsoar.config_type: "
                    f"\"{BACKEND_CONFIG_TYPE}\"` but is NOT one of the "
                    f"whitelisted canonical fields "
                    f"({', '.join(sorted(WHITELISTED_BACKEND_PARAMS))}). "
                    f"Remove the marker or rename the field"
                )

            if defect is None:
                continue
            if (runtime_name, defect) in seen:
                continue
            seen.add((runtime_name, defect))

            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        handler_id=handler.id,
                        field_id=runtime_name,
                        source_file=vf.origin.file_label,
                        location_hint=f" ({vf.location_hint})",
                        problem=problem,
                    ),
                    content_object=connector,
                    path=vf.source_file,
                )
            )

        return results
