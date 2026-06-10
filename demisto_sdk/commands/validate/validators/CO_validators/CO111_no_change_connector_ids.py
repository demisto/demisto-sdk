from __future__ import annotations

from typing import Dict, Iterable, List, Set, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Connector


class NoChangeConnectorIdsValidator(BaseValidator[ContentTypes]):
    error_code = "CO111"
    description = (
        "Breaking-change check: ensure no ID in an XSOAR-supported connector "
        "is removed or renamed compared to the previously-committed version. "
        "Covers connector.yaml.id, capabilities.yaml capabilities[].id + "
        "sub_capabilities[].id, connection.yaml profiles[].id, and each "
        "handler.yaml id."
    )
    rationale = (
        "These IDs are referenced by other connector files, by upstream "
        "platform configuration, and by deployed instances on the "
        "platform. Removing or renaming any of them is a hard breaking "
        "change for users with provisioned instances and for any handler "
        "that targets the old id. Renames look like a remove + add to the "
        "diff, so this validator flags every old id that is missing from "
        "the new set (additions are non-breaking and pass)."
    )
    error_message = (
        "Connector '{connector_id}' removed or renamed the following IDs "
        "compared to the previous version. The following items ids were "
        "removed:\n{removed_details}"
    )
    related_field = "id"
    expected_git_statuses = [GitStatuses.RENAMED, GitStatuses.MODIFIED]
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Per-connector check: collect every ID from the OLD content object,
        group by file type, diff against the NEW set.

        Trigger gate: only XSOAR-supported connectors (those with at least
        one handler whose ``is_xsoar`` is True). Non-XSOAR connectors are
        skipped (consistent with the CO123 / CO118-family gate).

        For each XSOAR-supported connector, build per-file removed-id maps:

          - connector.yaml: [old.object_id] vs [new.object_id]
          - capabilities.yaml: union of cap.id + sub.id (old vs new)
          - connection.yaml: profile.id for every profile (old vs new)
          - handler.yaml (per handler): handler.id (old vs new), keyed by
            the handler's directory name so renames within the same dir
            are still surfaced

        Additions are non-breaking and ignored. Any old ID that is missing
        from the new set is reported. All removed IDs for one connector are
        merged into ONE ValidationResult with a per-file line-itemized
        message.
        """
        results: List[ValidationResult] = []
        for connector in content_items:
            old_obj = cast(
                Connector, getattr(connector, "old_base_content_object", None)
            )
            if old_obj is None:
                # No previous version to diff against -> nothing to validate.
                # (Git status filters keep this branch unlikely in practice.)
                continue

            # Trigger gate: only XSOAR-supported connectors. We use the NEW
            # connector's xsoar_handlers so a previously-XSOAR connector that
            # has been fully migrated away from XSOAR is no longer gated by
            # this validator (its breaking changes are out of CO111's remit).
            if not connector.xsoar_handlers:
                continue

            removed_by_file: Dict[str, List[str]] = self._collect_removed_ids(
                old_obj, connector
            )
            if not removed_by_file:
                continue

            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        removed_details=self._format_removed(removed_by_file),
                    ),
                    content_object=connector,
                )
            )
        return results

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _collect_removed_ids(
        old_connector: Connector, new_connector: Connector
    ) -> Dict[str, List[str]]:
        """Build ``{file_label: [removed_ids...]}`` for IDs present in OLD
        but missing from NEW. Empty dict means no removals (validation
        passes for this connector).
        """
        removed: Dict[str, List[str]] = {}

        # connector.yaml — connector-level object_id
        old_connector_id = old_connector.object_id
        if old_connector_id and old_connector_id != new_connector.object_id:
            removed["connector.yaml"] = [old_connector_id]

        # capabilities.yaml — capability ids + nested sub_capability ids
        old_cap_ids: Set[str] = set()
        for cap in old_connector.capabilities:
            old_cap_ids.add(cap.id)
            for sub in cap.sub_capabilities:
                old_cap_ids.add(sub.id)
        new_cap_ids: Set[str] = set()
        for cap in new_connector.capabilities:
            new_cap_ids.add(cap.id)
            for sub in cap.sub_capabilities:
                new_cap_ids.add(sub.id)
        cap_missing = sorted(old_cap_ids - new_cap_ids)
        if cap_missing:
            removed["capabilities.yaml"] = cap_missing

        # connection.yaml — profile ids
        old_profile_ids: Set[str] = set()
        if old_connector.connection:
            old_profile_ids = {p.id for p in old_connector.connection.profiles}
        new_profile_ids: Set[str] = set()
        if new_connector.connection:
            new_profile_ids = {p.id for p in new_connector.connection.profiles}
        profile_missing = sorted(old_profile_ids - new_profile_ids)
        if profile_missing:
            removed["connection.yaml"] = profile_missing

        # handler.yaml — per-handler ID, keyed by directory name so a rename
        # within the same dir is reported against the dir the user actually
        # changed. A whole-dir deletion is also reported (old dir present,
        # new dir absent) — same intent: an id the platform used to know is
        # gone.
        old_by_dir = {h.handler_dir_name: h.id for h in old_connector.handlers}
        new_by_dir = {h.handler_dir_name: h.id for h in new_connector.handlers}
        for dir_name, old_id in sorted(old_by_dir.items()):
            new_id = new_by_dir.get(dir_name)
            if new_id is None:
                # Whole handler dir removed.
                removed[f"components/handlers/{dir_name}/handler.yaml"] = [old_id]
            elif new_id != old_id:
                # Handler dir kept but id renamed.
                removed[f"components/handlers/{dir_name}/handler.yaml"] = [old_id]

        return removed

    @staticmethod
    def _format_removed(removed_by_file: Dict[str, List[str]]) -> str:
        """Render the per-file removed-id map deterministically."""
        return "\n".join(
            f"  {file_label}: {ids}"
            for file_label, ids in sorted(removed_by_file.items())
        )
