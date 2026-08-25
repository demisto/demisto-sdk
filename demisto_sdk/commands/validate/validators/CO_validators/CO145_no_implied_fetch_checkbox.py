"""CO145 - NoImpliedFetchCheckbox.

Per §3.4 note 5 / §3.7 of the standard connector guide, the "implied
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

Source of truth is ``handler.resolved_params`` - built by
``ConnectorParser._build_resolved_params`` in
``demisto_sdk/commands/content_graph/parsers/connector.py``. That
collection walks only *user-facing field entries* from four
locations:

1. ``connection.yaml`` ``general_configurations``
2. ``connection.yaml`` ``profiles[]`` bound to this handler
3. ``capabilities.yaml`` ``general_configurations``
4. ``configurations.yaml`` entries for capabilities the handler
   subscribes to

Serializer ``computed_fields`` outputs are **not** included - they
live on ``handler.serializer.computed_fields``, a separate collection.
So a legitimate ``computed_fields``-driven ``isFetch: true``
(CO130 / CO171 shape) will NOT trigger CO145. This is the whole
point of the design: the user checkbox is forbidden, the
serializer-emitted backend flag is required.

We match on ``content_param_name`` (the post-serializer runtime name
the integration would receive) rather than ``connector_param_name``
(the raw YAML id). A grouped connector may namespace the checkbox
(e.g. ``xsoar-akamai-waf-siem_isFetchEvents``) and rename it back
via ``serializer.yaml`` ``field_mappings``; either way the integration
still gets a user-controllable ``isFetchEvents`` value, which is
exactly what CO145 forbids.

Granularity: one ``ValidationResult`` per (handler, forbidden field)
finding. ``path`` is set to the concrete on-disk location of the
YAML file identified by the resolved-param's ``source_file`` string,
so the standard ``[file:<...>]`` ignore chain in ``.connector-ignore``
targets the right file. A connector that legitimately needs one
specific checkbox (e.g. ``akamai`` keeping ``isFetchEvents`` on the
``akamai-waf-siem`` log-collection profile) can silence CO145 for
that file only:

    [file:configurations.yaml]
    ignore=CO145

Non-XSOAR handlers are skipped (mirrors CO120 / CO130 / CO136).
The forbidden-checkbox contract is XSOAR-migration-specific (§3.7);
non-XSOAR handlers still have ``resolved_params`` populated, but
we do not police them here.
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
# message - the validator itself never inspects the connector's
# declared capabilities. The rule is purely "these ids must never
# appear as YAML field entries in the XSOAR-visible surface", which
# is stronger than "must not appear when the capability is declared"
# and easier to explain to authors.
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
        "'{source_file}'. Remove the field entry - the backend flag "
        "must be delivered via serializer.yaml `computed_fields` "
        "gated on the capability (see CO130 / CO171)."
    )
    related_field = "resolved_params"
    is_auto_fixable = False
    # A finding may originate from any of connection.yaml,
    # capabilities.yaml, or configurations.yaml. Listing all three
    # in ``related_file_type`` keeps the ``.connector-ignore`` preflight
    # (``ConnectorsValidator.should_run`` -> ``is_error_ignored`` ->
    # ``_resolve_ignore_file_keys``) able to short-circuit whichever
    # per-file suppression the author wrote - same rationale documented
    # on CO130.
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
            file_paths = self._source_file_paths(connector)
            for handler in connector.xsoar_handlers:
                results.extend(self._check_handler(connector, handler, file_paths))

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _source_file_paths(connector: Connector) -> Dict[str, Optional[Path]]:
        """Map ``ResolvedParamMapping.source_file`` string values to the
        concrete on-disk ``Path`` for the corresponding file.

        ``source_file`` is one of the three literals set by
        ``ConnectorParser._collect_handler_fields``:

        - ``"connection.yaml"``
        - ``"capabilities.yaml"``
        - ``"configurations.yaml"``

        Each is mapped to the connector's ``*_file.file_path``. When
        a related-file object reports ``exist=False`` we still return
        its ``file_path`` (which points at the expected on-disk
        location) so ignore keys line up with what an author would
        type in ``.connector-ignore``. A ``None`` fallback is kept
        for safety in case the parser changes; downstream ignore
        resolution handles ``None`` gracefully (safe default: not
        ignored).
        """
        return {
            "connection.yaml": connector.connection_file.file_path,
            "capabilities.yaml": connector.capabilities_file.file_path,
            "configurations.yaml": connector.configurations_file.file_path,
        }

    def _check_handler(
        self,
        connector: Connector,
        handler: HandlerData,
        file_paths: Dict[str, Optional[Path]],
    ) -> List[ValidationResult]:
        """Emit one ``ValidationResult`` per (handler, forbidden field)
        finding.

        Match key is ``rp.content_param_name`` (post-serializer
        runtime name). A grouped-connector namespaced checkbox that
        gets renamed back to a forbidden id by
        ``serializer.yaml field_mappings`` still lands in the
        forbidden set - which is correct, because the integration
        would still receive a user-controllable ``isFetch*`` value.

        Findings are deduplicated by ``content_param_name`` per
        handler: the same forbidden id can technically appear more
        than once in ``resolved_params`` (e.g. multiple auth
        profiles both mounting a shared checkbox), but the author
        fixes it once and the message would be identical. The
        ``source_file`` reported is the first occurrence seen -
        deterministic given ``_collect_handler_fields`` iteration
        order (connection general -> connection profiles ->
        capabilities general -> configurations per capability).
        """
        results: List[ValidationResult] = []
        seen: Set[str] = set()

        for rp in handler.resolved_params:
            runtime_name = rp.content_param_name
            if runtime_name not in FORBIDDEN_FETCH_CHECKBOX_NAMES:
                continue
            if runtime_name in seen:
                continue
            seen.add(runtime_name)

            capability_id = FORBIDDEN_FETCH_CHECKBOXES[runtime_name]
            source_file = rp.source_file or "connector"
            path = file_paths.get(source_file)

            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        handler_id=handler.id,
                        field_id=runtime_name,
                        capability_id=capability_id,
                        source_file=source_file,
                    ),
                    content_object=connector,
                    path=path,
                )
            )

        return results
