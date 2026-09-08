"""CO137 - every ``duration`` field visible to an XSOAR handler must
conform to the mandatory duration-field shape.


    Rules: `output_format` MUST be "minutes"; `units` MUST be
    ["days","hours","minutes"] (mandatory set & order); per-unit
    caps are `hours <= 23`, `minutes <= 59`, `days` uncapped.

CO137 iterates every XSOAR
handler and inspects every ``field_type == "duration"`` field the
unified :func:`Connector.visible_fields_for_handler` walker returns
for that handler. A duration field visible to NO XSOAR handler is
ignored.

Sub-rules enforced per duration field:
    A. ``options.units == ["days", "hours", "minutes"]`` exactly.
    B. ``options.output_format == "minutes"``.
    C. ``options.default_value.hours <= 23`` when ``hours`` key present.
    D. ``options.default_value.minutes <= 59`` when ``minutes`` key present.

Per-field dedup: multiple XSOAR handlers may see the same physical
duration field (e.g. a shared connection.general_configurations
field). We dedupe by ``(source_file, raw_id, capability_id or
profile_id)`` so authors don't get the same defect reported N times
for N handlers that share a field.

``path`` on the aggregated result points at the file that carries
the FIRST offending field, preserving the pre-migration behaviour.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

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

# ============================================================
# CO137 constants (guide §2.11)
# ============================================================
EXPECTED_UNITS: List[str] = ["days", "hours", "minutes"]
EXPECTED_OUTPUT_FORMAT: str = "minutes"
MAX_HOURS: int = 23
MAX_MINUTES: int = 59
DURATION_FIELD_TYPE: str = "duration"


# ============================================================
# Origin -> source-file label mapping (message hint).
#
# Walker migration: the walker exposes ``vf.origin.file_label``
# ("connection.yaml" / "capabilities.yaml" / "configurations.yaml")
# directly, so we don't need to map by hand. But keeping this local
# alias documents the two files CO137 cares about — 
# capabilities.yaml is intentionally excluded because duration fields live in
# connection.yaml (general + profiles) and configurations.yaml
# (general + per-capability) only.
# ============================================================
_CONNECTION_YAML_ORIGINS = frozenset(
    {
        FieldOrigin.CONNECTION_GENERAL,
        FieldOrigin.CONNECTION_PROFILE,
    }
)
_CONFIGURATIONS_YAML_ORIGINS = frozenset(
    {
        FieldOrigin.CONFIGURATIONS_GENERAL,
        FieldOrigin.CONFIGURATIONS_CAPABILITY,
    }
)


def _location_label(vf: HandlerVisibleField) -> str:
    """Return the CO137-style ``"<file>.yaml <location>"`` string used
    in error messages. Matches the pre-migration layout so authors see
    the same phrasing.
    """
    file_label = vf.origin.file_label
    return f"{file_label} {vf.location_hint}"


def _dedup_key(
    vf: HandlerVisibleField,
) -> Tuple[str, str, Optional[str], Optional[str]]:
    """Per-physical-field dedup key.

    A duration field that's visible to N handlers should only be
    checked (and reported) once. Physical identity is
    (source_file, raw_id, capability_id, profile_id) — the two
    latter disambiguate a shared field-id that appears in multiple
    capability entries or profiles.
    """
    return (
        str(vf.source_file),
        vf.raw_id,
        vf.capability_id,
        vf.profile_id,
    )


# ============================================================
# Per-field sub-rule checks
# ============================================================
def _check_duration_field(field: Dict[str, Any], where: str) -> List[str]:
    """Return a list of sub-rule failure strings for ``field``. Empty
    list means the field passes all CO137 sub-rules. ``field`` is the
    raw YAML dict (via ``HandlerVisibleField.raw_dict``) so leaf
    values that the pydantic model may not round-trip losslessly
    stay faithful."""
    issues: List[str] = []
    fid = field.get("id", "<unknown-id>")
    prefix = f"{where} field '{fid}'"

    options = field.get("options")
    if not isinstance(options, dict):
        issues.append(
            f"{prefix} has no `options` mapping - required for a duration field"
        )
        return issues

    # A: units == ["days", "hours", "minutes"] exactly.
    units = options.get("units")
    if units != EXPECTED_UNITS:
        issues.append(
            f"{prefix}: options.units={units!r} but must be "
            f"{EXPECTED_UNITS!r} (exact list, in that order)"
        )

    # B: output_format == "minutes".
    output_format = options.get("output_format")
    if output_format != EXPECTED_OUTPUT_FORMAT:
        issues.append(
            f"{prefix}: options.output_format={output_format!r} but "
            f"must be {EXPECTED_OUTPUT_FORMAT!r}"
        )

    # C + D: default_value per-unit caps.
    default_value = options.get("default_value")
    if isinstance(default_value, dict):
        hours = default_value.get("hours")
        if isinstance(hours, int) and hours > MAX_HOURS:
            issues.append(
                f"{prefix}: options.default_value.hours={hours} but "
                f"must be <= {MAX_HOURS} (guide §2.11)"
            )
        minutes = default_value.get("minutes")
        if isinstance(minutes, int) and minutes > MAX_MINUTES:
            issues.append(
                f"{prefix}: options.default_value.minutes={minutes} "
                f"but must be <= {MAX_MINUTES} (guide §2.11)"
            )

    return issues


# ============================================================
# CO137 validator
# ============================================================
class IsValidDurationTypeParamValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO137"
    description = (
        "Validates that every duration-typed field visible to an "
        "XSOAR handler (walker-scoped) declares the canonical "
        "duration-field shape: options.units == "
        "['days','hours','minutes'], options.output_format == "
        "'minutes', and per-unit default_value caps hours<=23 and "
        "minutes<=59. Serializer field_mappings and view_group / "
        "required_for_capabilities visibility scoping are applied by "
        "the walker."
    )
    rationale = (
        "The platform serializes a duration field into a single "
        "minutes integer using the declared units order. Deviating "
        "from the canonical units list or output_format breaks the "
        "serialization contract - the BE will either receive the "
        "wrong scalar or reject the value entirely. Per-unit caps "
        "reflect the natural rollover (24h -> 1d, 60m -> 1h) that "
        "authors are expected to normalize into the higher unit "
        "instead of leaving as an oversized value."
    )
    error_message = (
        "Connector '{connector_id}' has invalid duration-type field(s): {issues}"
    )
    related_field = "duration"
    is_auto_fixable = False
    related_file_type = [
        RelatedFileType.CONNECTOR_CONNECTION,
        RelatedFileType.CONNECTOR_CONFIGURATIONS,
    ]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            issues, path = self._check_connector(connector)
            if not issues:
                continue
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        issues="; ".join(issues),
                    ),
                    content_object=connector,
                    path=path,
                )
            )
        return results

    def _check_connector(
        self, connector: Connector
    ) -> Tuple[List[str], Optional[Path]]:
        """Walk every XSOAR handler; for each handler collect its
        visible duration fields via the walker; dedupe by physical
        identity so a shared field is checked once; run the sub-rule
        checks. Returns (issues, path-to-first-offending-file)."""
        issues: List[str] = []
        first_bad_path: Optional[Path] = None
        seen: set = set()

        for handler in connector.xsoar_handlers:
            for vf in self._iter_visible_duration_fields(connector, handler):
                key = _dedup_key(vf)
                if key in seen:
                    continue
                seen.add(key)

                # Capabilities.yaml duration fields would be dead content
                # per §2.11 (which puts duration fields under
                # connection/configurations only) — guard defensively.
                if vf.origin not in _CONNECTION_YAML_ORIGINS | _CONFIGURATIONS_YAML_ORIGINS:
                    continue

                raw_dict = vf.raw_dict or {}
                field_issues = _check_duration_field(
                    raw_dict, _location_label(vf)
                )
                if field_issues:
                    if first_bad_path is None:
                        first_bad_path = Path(vf.source_file)
                    issues.extend(field_issues)

        return issues, first_bad_path

    @staticmethod
    def _iter_visible_duration_fields(
        connector: Connector, handler: HandlerData
    ) -> Iterable[HandlerVisibleField]:
        """Yield every ``HandlerVisibleField`` visible to ``handler``
        whose parsed field has ``field_type == "duration"``.

        We inspect the parsed ``field.field_type`` (not the raw dict)
        because the walker already parsed the field via
        :meth:`ConnectorParser._parse_field` — same authoritative
        parse the connector-parser used, so the type check matches
        the platform's runtime interpretation.
        """
        for vf in connector.visible_fields_for_handler(handler):
            if vf.field.field_type == DURATION_FIELD_TYPE:
                yield vf
