"""CO145 - NoImpliedFetchCheckbox.

The "implied
fetch checkbox" for a declared collection capability MUST NOT be
emitted as a user-visible field on the connector. Choosing the
capability IS the opt-in - the fetch flag itself is delivered to the
integration via ``serializer.yaml`` ``computed_fields`` (see CO130 /
CO171 for the positive rule).

Forbidden emissions (as user fields):

- ``isFetch``            (fetch-issues)
- ``feed``               (threat-intelligence-and-enrichment)
- ``isFetchEvents``      (log-collection)
- ``isFetchAssets``      (fetch-assets-and-vulnerabilities)
- ``isFetchCredentials`` (fetch-secrets)

Match on **runtime name** (post ``serializer.yaml``
``field_mappings`` rename) so grouped-connector namespaced ids
(e.g. ``xsoar-akamai-waf-siem_isFetchEvents``) renamed back to a
forbidden id still fail — the integration would still receive a
user-controllable value.

We consume the unified handler-visible-fields walker
(:meth:`Connector.visible_fields_for_handler`) which already covers
every physical location a forbidden checkbox can hide:
``connection.yaml`` general + profiles bound to the handler,
``capabilities.yaml`` general, and ``configurations.yaml`` general
+ per-capability entries (including grouped sub-cap ids the
parser silently drops from ``self.capabilities``). Serializer
``computed_fields`` outputs are intentionally OUTSIDE the walker
(spec §7 Q3): the legitimate ``computed_fields``-driven fetch flag
(CO130 / CO171 shape) is not policed here.

Granularity: one ``ValidationResult`` per (handler, forbidden field)
finding. Findings are deduplicated by runtime name per handler; the
same forbidden id can appear more than once (e.g. general configs +
a per-cap entry), but authors fix it once at the source. First-seen
in walker order wins; walker order is CONNECTION_GENERAL →
CONNECTION_PROFILE → CAPABILITIES_GENERAL → CONFIGURATIONS_GENERAL
→ CONFIGURATIONS_CAPABILITY.

Non-XSOAR handlers are skipped (mirrors CO120 / CO130 / CO136).
The forbidden-checkbox contract is XSOAR-migration-specific;
non-XSOAR handlers are not policed by CO145.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Optional, Set

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

# The 5 forbidden user-checkbox ids, keyed by the capability that
# implies each. The capability id is included only for the error
# message; the validator itself never inspects the connector's
# declared capabilities.
FORBIDDEN_FETCH_CHECKBOXES: Dict[str, str] = {
    "isFetch": "fetch-issues",
    "feed": "threat-intelligence-and-enrichment",
    "isFetchEvents": "log-collection",
    "isFetchAssets": "fetch-assets-and-vulnerabilities",
    "isFetchCredentials": "fetch-secrets",
}
FORBIDDEN_FETCH_CHECKBOX_NAMES: FrozenSet[str] = frozenset(
    FORBIDDEN_FETCH_CHECKBOXES.keys()
)


class NoImpliedFetchCheckboxValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO145"
    description = (
        "Forbid emitting the implied fetch checkbox for a declared "
        "collection capability as a user-visible field. The 5 "
        "forbidden ids are isFetch / feed / isFetchEvents / "
        "isFetchAssets / isFetchCredentials. Choosing the capability "
        "IS the opt-in; the backend flag itself must be emitted via "
        "serializer.yaml computed_fields (CO130 / CO171)."
    )
    rationale = (
        "In UCP the collection capabilities are declarative - picking "
        "the capability wires the fetch job in the backend. Also "
        "exposing the legacy fetch-flag checkbox to the user creates "
        "two independent switches for the same behavior, which is "
        "both confusing and a source of drift (the checkbox and the "
        "capability can disagree). The serializer computed_fields "
        "shape is the only supported channel for delivering the "
        "backend fetch flag; the user checkbox must be omitted."
    )
    error_message = (
        "Connector '{connector_id}' handler '{handler_id}': "
        "forbidden implied-fetch checkbox '{field_id}' (capability "
        "'{capability_id}') is emitted as a user-visible field in "
        "'{source_file}' ({location_hint}). Remove the field entry - "
        "the backend flag must be delivered via serializer.yaml "
        "`computed_fields` gated on the capability (see CO130 / "
        "CO171)."
    )
    related_field = "configurations"
    is_auto_fixable = False
    # A finding may originate from any of connection.yaml,
    # capabilities.yaml, or configurations.yaml. Listing all three
    # keeps the ``.connector-ignore`` preflight
    # (``ConnectorsValidator.should_run`` -> ``is_error_ignored`` ->
    # ``_resolve_ignore_file_keys``) able to short-circuit whichever
    # per-file suppression the author wrote - same rationale
    # documented on CO130.
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

    def _check_handler(
        self,
        connector: Connector,
        handler: HandlerData,
    ) -> List[ValidationResult]:
        """Emit one ``ValidationResult`` per unique forbidden runtime
        name visible to ``handler``.

        The walker yields fields in a deterministic order across all
        five origins (see module docstring); we take the first
        occurrence per runtime name so authors get a single, actionable
        location to fix even when the same forbidden id is duplicated
        across surfaces.
        """
        results: List[ValidationResult] = []
        seen: Set[str] = set()

        for vf in connector.visible_fields_for_handler(handler):
            runtime_name = vf.runtime_name
            if runtime_name not in FORBIDDEN_FETCH_CHECKBOX_NAMES:
                continue
            if runtime_name in seen:
                continue
            seen.add(runtime_name)

            path: Optional[Path] = vf.source_file
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        handler_id=handler.id,
                        field_id=runtime_name,
                        capability_id=FORBIDDEN_FETCH_CHECKBOXES[runtime_name],
                        source_file=vf.origin.file_label,
                        location_hint=vf.location_hint,
                    ),
                    content_object=connector,
                    path=path,
                )
            )

        return results
