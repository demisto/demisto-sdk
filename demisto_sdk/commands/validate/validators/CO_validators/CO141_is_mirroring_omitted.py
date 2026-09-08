"""CO141 - IsMirroringOmittedValidator.

Mirroring is
**out of scope on the Platform**. The two mirroring params
(``outgoingMapperId``, ``defaultMapperOut``) MUST NOT be emitted
as user-visible YAML field entries anywhere in the XSOAR-visible
surface of a connector, and MUST NOT be smuggled to the integration
via a ``serializer.yaml`` ``computed_fields`` output rule.

Design rationale:

- **Match key is the post-serializer runtime name** — the walker
  applies the ``serializer.yaml`` ``field_mappings`` rename before
  emitting each :class:`HandlerVisibleField`, so grouped connectors
  that namespace the field id (e.g. ``xsoar-foo_outgoingMapperId``
  → ``outgoingMapperId``) still fail.

- **Serializer ``computed_fields`` are also policed** — a rule that
  outputs an ``outgoingMapperId`` / ``defaultMapperOut`` value at
  runtime is equally forbidden, because the integration still ends
  up receiving the mirroring param even though it never appears in
  a user-visible YAML field entry. Defense-in-depth against the
  "smuggle a mirroring param via computed_fields" workaround.

- **Ignore key routes per source file** — a connector that legit
  needs to keep mirroring on for backward-compat (unlikely, given
  §3.2) can silence per file via
  ``[file:<...>] ignore=CO141`` in ``.connector-ignore``.

Non-XSOAR handlers are skipped.
"""

from __future__ import annotations

from pathlib import Path
from typing import FrozenSet, Iterable, List, Optional, Set

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

# The 2 forbidden mirroring param ids. Kept as a bare set (not a
# {id: reason} mapping like CO145's dict) because the "why" is the
# same for both - mirroring is out of scope on Platform.
FORBIDDEN_MIRRORING_PARAMS: FrozenSet[str] = frozenset(
    {"outgoingMapperId", "defaultMapperOut"}
)


class IsMirroringOmittedValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO141"
    description = (
        "Forbid emitting mirroring params (`outgoingMapperId`, "
        "`defaultMapperOut`) as user-visible YAML field entries in "
        "the XSOAR-visible surface of a connector, or via serializer "
        "`computed_fields` output rules. Mirroring is out of scope on "
        "the Platform."
    )
    rationale = (
        "The XSOAR Platform does not support outgoing mirroring - "
        "the runtime has no consumer for these params, so exposing "
        "them to the user is misleading (the setting has no effect) "
        "and pollutes the instance-creation form. A serializer "
        "computed_fields rule emitting one of them is equally invalid "
        "- it delivers the param to the integration by a different "
        "channel. Any legacy integration YML that still declares these "
        "params must be stripped from the connector's user-visible "
        "surface AND from serializer.yaml at migration time."
    )
    error_message = (
        "Connector '{connector_id}' handler '{handler_id}': "
        "forbidden mirroring param '{field_id}' is emitted in "
        "'{source_file}'{location_hint}. "
        "Remove the entry - mirroring is out of scope on Platform."
    )
    related_field = "configurations"
    is_auto_fixable = False
    # A finding may originate from any of the three YAML files OR the
    # serializer.yaml computed_fields channel, so listing all four in
    # ``related_file_type`` keeps the ``.connector-ignore`` preflight
    # (``ConnectorsValidator.should_run`` -> ``is_error_ignored`` ->
    # ``_resolve_ignore_file_keys``) able to short-circuit whichever
    # per-file suppression the author wrote.
    related_file_type = [
        RelatedFileType.CONNECTOR_CONNECTION,
        RelatedFileType.CONNECTOR_CAPABILITIES,
        RelatedFileType.CONNECTOR_CONFIGURATIONS,
        RelatedFileType.CONNECTOR_SERIALIZER,
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
        """Emit one ``ValidationResult`` per (handler, forbidden field)
        finding. Deduplicated by runtime name per handler across both
        the user-visible-field walker and the serializer
        ``computed_fields`` scan.
        """
        results: List[ValidationResult] = []
        seen: Set[str] = set()

        # 1) User-visible YAML field entries (three-file walker).
        for vf in connector.visible_fields_for_handler(handler):
            runtime_name = vf.runtime_name
            if runtime_name not in FORBIDDEN_MIRRORING_PARAMS:
                continue
            if runtime_name in seen:
                continue
            seen.add(runtime_name)

            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        handler_id=handler.id,
                        field_id=runtime_name,
                        source_file=vf.origin.file_label,
                        location_hint=f" ({vf.location_hint})",
                    ),
                    content_object=connector,
                    path=vf.source_file,
                )
            )

        # 2) Serializer computed_fields (defense-in-depth). A rule
        # that outputs a mirroring param at runtime is equally
        # forbidden even though it never appears as a user-visible
        # YAML field entry.
        for out_id in sorted(
            handler.serializer_computed_output_ids() & FORBIDDEN_MIRRORING_PARAMS
        ):
            if out_id in seen:
                continue
            seen.add(out_id)
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        handler_id=handler.id,
                        field_id=out_id,
                        source_file="serializer.yaml",
                        location_hint=" (computed_fields)",
                    ),
                    content_object=connector,
                    path=handler.serializer_path,
                )
            )

        return results
