"""CO146 - merged CO146 + CO147 - summary.yaml must exist and its
metadata block must match the canonical wording.

Per manifest bands:
    - CO146 `IsSummaryPresent` (Both): every migrated connector MUST
      ship a `summary.yaml` file.
    - CO147 `IsValidSummaryMetadata` (Both): `summary.yaml`
      `metadata.title` must equal "Summary" and `metadata.description`
      must equal "Review your instance configuration".

Merged rationale: The two rules operate on the same file with a natural
dependency — you can only check metadata contents if the file exists —
so a single validator with aggregated findings avoids double-reporting
the same connector when both rules would fire in isolation.

Skip cases: none. Every connector must ship a valid summary.yaml. (For
non-XSOAR-related connectors that are not selected by the runner, this
validator simply won't be invoked.)

All violations aggregate into a single ValidationResult per connector.
The result's `path` points at `summary.yaml` (whether or not it exists
on disk — the RelatedFile accessor still resolves the expected path).
"""

from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

# ============================================================
# Canonical values (per manifest CO146/CO147)
# ============================================================
EXPECTED_TITLE = "Summary"
EXPECTED_DESCRIPTION = "Review your instance configuration"


# ============================================================
# CO146 (merged CO146 + CO147) validator
# ============================================================
class IsSummaryPresentAndValidMetadataValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO146"
    description = (
        "Validates that every connector ships a `summary.yaml` file "
        "and that its `metadata.title` equals 'Summary' and "
        "`metadata.description` equals 'Review your instance "
        "configuration'."
    )
    rationale = (
        "From a pure connector POV `summary.yaml` is optional, but "
        "from the XSOAR content POV it is REQUIRED — every migrated "
        "connector must ship a summary block so the XSOAR UI can "
        "render the post-onboarding review page with consistent "
        "wording across all connectors. Merges the presence and "
        "metadata rules into one check because they operate on the "
        "same file with a natural dependency."
    )
    error_message = "Connector '{connector_id}': summary.yaml is invalid: {issues}"
    related_field = "summary"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_SUMMARY]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for connector in content_items:
            issues = self._check_connector(connector)
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
                    path=connector.summary_file.file_path,
                )
            )
        return results

    def _check_connector(self, connector: Connector) -> List[str]:
        """Return aggregated issue strings; empty list if all good."""
        summary_file = connector.summary_file

        # Rule 1 (was CO146): file must exist on disk.
        if not summary_file.exist:
            return [
                "summary.yaml is missing (every migrated connector "
                "must ship a summary.yaml file)"
            ]

        # Rule 2 (was CO147): metadata title + description.
        issues: List[str] = []
        raw = summary_file.file_content
        if not isinstance(raw, dict):
            return [
                "summary.yaml is present but its top-level content is "
                "not a mapping (expected a YAML dict with a "
                "`metadata` block)"
            ]

        metadata = raw.get("metadata")
        if not isinstance(metadata, dict):
            return [
                "summary.yaml is missing the required `metadata` "
                "mapping (expected `metadata.title` and "
                "`metadata.description`)"
            ]

        title = metadata.get("title")
        if title != EXPECTED_TITLE:
            issues.append(
                f"metadata.title={title!r} but must be " f"{EXPECTED_TITLE!r}"
            )

        description = metadata.get("description")
        if description != EXPECTED_DESCRIPTION:
            issues.append(
                f"metadata.description={description!r} but must be "
                f"{EXPECTED_DESCRIPTION!r}"
            )

        return issues
