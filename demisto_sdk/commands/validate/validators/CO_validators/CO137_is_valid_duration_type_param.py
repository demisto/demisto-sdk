"""CO137 - every ``duration`` field must conform to the mandatory
duration-field shape.

Per guide §2.11 + Appendix A row 19:

    Rules: `output_format` MUST be "minutes"; `units` MUST be
    ["days","hours","minutes"] (mandatory set & order); per-unit
    caps are `hours <= 23`, `minutes <= 59`, `days` uncapped.

CO137 walks every field with ``field_type == "duration"`` across
BOTH files that carry them:

- ``connection.yaml``:
    - ``general_configurations.configurations[*].fields[*]`` (Standard
      connectors)
    - ``profiles[*].configurations[*].fields[*]`` (grouped connectors)
- ``configurations.yaml``:
    - ``general_configurations.configurations[*].fields[*]``
    - ``configurations[*].configurations[*].fields[*]`` (per-capability)

Sub-rules enforced per duration field:
    A. ``options.units == ["days", "hours", "minutes"]`` exactly.
    B. ``options.output_format == "minutes"``.
    C. ``options.default_value.hours <= 23`` when ``hours`` key present.
    D. ``options.default_value.minutes <= 59`` when ``minutes`` key present.

All sub-rule failures are aggregated into a single ValidationResult
per connector. ``path`` points at the file that carries the FIRST
offending field.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from demisto_sdk.commands.content_graph.objects.connector import Connector
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
# Traversal
# ============================================================
def _iter_field_groups(container: Any) -> Iterable[Dict[str, Any]]:
    """Yield every raw field-group dict from a
    ``general_configurations`` / ``profile.configurations`` /
    ``capability.configurations`` container.

    Container shape (per schema):
        container.configurations[*] -> FieldGroup dict
    """
    if not isinstance(container, dict):
        return
    groups = container.get("configurations")
    if not isinstance(groups, list):
        return
    for group in groups:
        if isinstance(group, dict):
            yield group


def _iter_fields_in_group(group: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """Yield every raw field dict from ``group.fields[]``."""
    fields = group.get("fields")
    if not isinstance(fields, list):
        return
    for field in fields:
        if isinstance(field, dict):
            yield field


def _iter_duration_fields_from_file(
    raw: Optional[Dict[str, Any]],
) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """Yield (source_label, field_dict) for every ``duration`` field
    found anywhere in the given YAML dict.

    Handles all 4 locations across connection.yaml AND configurations.yaml:
    - ``general_configurations`` (top-level in both files)
    - ``profiles[*].configurations`` (connection.yaml only in practice)
    - ``configurations[*].configurations`` (configurations.yaml only)
    """
    if not isinstance(raw, dict):
        return

    # 1) top-level general_configurations
    gc = raw.get("general_configurations")
    for group in _iter_field_groups(gc):
        for field in _iter_fields_in_group(group):
            if field.get("field_type") == DURATION_FIELD_TYPE:
                yield ("general_configurations", field)

    # 2) profiles (connection.yaml grouped shape)
    profiles = raw.get("profiles")
    if isinstance(profiles, list):
        for profile in profiles:
            if not isinstance(profile, dict):
                continue
            pid = profile.get("id", "<unknown-profile>")
            for group in _iter_field_groups(profile):
                for field in _iter_fields_in_group(group):
                    if field.get("field_type") == DURATION_FIELD_TYPE:
                        yield (f"profile '{pid}'", field)

    # 3) per-capability configurations (configurations.yaml shape)
    caps = raw.get("configurations")
    if isinstance(caps, list):
        for cap in caps:
            if not isinstance(cap, dict):
                continue
            cid = cap.get("id", "<unknown-capability>")
            for group in _iter_field_groups(cap):
                for field in _iter_fields_in_group(group):
                    if field.get("field_type") == DURATION_FIELD_TYPE:
                        yield (f"capability '{cid}'", field)


# ============================================================
# Per-field sub-rule checks
# ============================================================
def _check_duration_field(
    field: Dict[str, Any], source_file: str, location: str
) -> List[str]:
    """Return a list of sub-rule failure strings for ``field``. Empty
    list means the field passes all CO137 sub-rules."""
    issues: List[str] = []
    fid = field.get("id", "<unknown-id>")
    prefix = f"{source_file} {location} field '{fid}'"

    options = field.get("options")
    if not isinstance(options, dict):
        issues.append(
            f"{prefix} has no `options` mapping - required for a " f"duration field"
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
        "Validates that every field with `field_type: duration` "
        "(anywhere in connection.yaml or configurations.yaml) declares "
        "the canonical duration-field shape: options.units == "
        "['days','hours','minutes'], options.output_format == "
        "'minutes', and per-unit default_value caps hours<=23 and "
        "minutes<=59."
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
        "Connector '{connector_id}' has invalid duration-type " "field(s): {issues}"
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
        """Walk every duration field on the connector and collect
        sub-rule failures. Returns (issues, path-to-first-offending-file).
        """
        issues: List[str] = []
        first_bad_path: Optional[Path] = None

        # connection.yaml
        conn_file = connector.connection_file
        if conn_file.exist:
            conn_raw = conn_file.file_content
            for location, field in _iter_duration_fields_from_file(conn_raw):
                field_issues = _check_duration_field(field, "connection.yaml", location)
                if field_issues:
                    if first_bad_path is None:
                        first_bad_path = conn_file.file_path
                    issues.extend(field_issues)

        # configurations.yaml
        conf_file = connector.configurations_file
        if conf_file.exist:
            conf_raw = conf_file.file_content
            for location, field in _iter_duration_fields_from_file(conf_raw):
                field_issues = _check_duration_field(
                    field, "configurations.yaml", location
                )
                if field_issues:
                    if first_bad_path is None:
                        first_bad_path = conf_file.file_path
                    issues.extend(field_issues)

        return issues, first_bad_path
