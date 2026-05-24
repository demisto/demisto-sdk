from __future__ import annotations

from typing import Dict, Iterable, List, Set, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Connector


class NoRemovedConnectorParamsValidator(BaseValidator[ContentTypes]):
    error_code = "CO110"
    description = (
        "Breaking-change check: ensure no existing parameter (field id) "
        "is deleted from an XSOAR-supported connector compared to the "
        "previously-committed version. Covers all three param buckets: "
        "general_configurations (capabilities-level), per-capability "
        "configurations, and auth params (connection.yaml general + "
        "per-profile). Renames count as removals unless the new handler "
        "serializer bridges the old id via a field_mappings entry "
        "(``{id: <new>, field_name: <old>}``)."
    )
    rationale = (
        "Field ids are referenced by upstream platform configuration and "
        "by deployed instances on the platform. Removing or renaming any "
        "field id breaks every instance that depended on it. Because "
        "renames look identical to remove+add in a diff, this validator "
        "flags every old field id that is missing from the new set. The "
        "serializer escape hatch deliberately bridges renames that the "
        "migration tooling performs via "
        "``dedup_field_id_and_register`` (id rename ``<field>`` -> "
        "``<handler>_<field>`` paired with a serializer entry). With the "
        "bridge in place the platform can still resolve the old id, so "
        "the rename is considered non-breaking."
    )
    error_message = (
        "Connector '{connector_id}' removed the following parameter ids "
        "compared to the previous version. The following ids were "
        "removed:\n{removed_details}"
    )
    related_field = "configurations"
    expected_git_statuses = [GitStatuses.RENAMED, GitStatuses.MODIFIED]
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Per-connector check: diff every field id (per bucket) between
        OLD and NEW, then forgive any old id that the NEW handler
        serializers bridge via ``field_mappings.field_name``.

        Trigger gate: only XSOAR-supported connectors (those with at least
        one handler whose ``is_xsoar`` is True). Non-XSOAR connectors are
        skipped (consistent with the CO109/CO111/CO117/CO119/CO123 gate).

        Bucket layout (each bucket is diffed independently):
          - ``capability '<cap_id>'``: every field under
            ``connector.capabilities[*].configurations[*].fields[*]``
            (the parser unifies capabilities.yaml general_configurations,
            configurations.yaml general_configurations, and per-capability
            configurations.yaml entries into this one list per capability)
          - ``connection.yaml (general_configurations)``: every field
            under ``connector.connection.general_configurations`` if set
          - ``connection.yaml (profile '<profile_id>')``: every field
            under each connection profile's ``configurations[*].fields[*]``

        Additions are non-breaking and ignored. Any old id missing from
        the new set is reported, unless the new serializer mappings list
        it as a ``field_name`` (bridging the rename). One ValidationResult
        per connector groups every removed id by bucket label.
        """
        results: List[ValidationResult] = []
        for connector in content_items:
            old_obj = cast(
                Connector, getattr(connector, "old_base_content_object", None)
            )
            if old_obj is None:
                # No previous version to diff against -> nothing to validate.
                continue

            # Trigger gate: only XSOAR-supported connectors.
            if not connector.xsoar_handlers:
                continue

            old_buckets: Dict[str, Set[str]] = self._collect_param_ids(old_obj)
            new_buckets: Dict[str, Set[str]] = self._collect_param_ids(connector)
            bridged: Set[str] = self._collect_serializer_bridged_old_ids(connector)

            removed_by_bucket: Dict[str, List[str]] = {}
            for bucket_label, old_ids in old_buckets.items():
                new_ids = new_buckets.get(bucket_label, set())
                missing = old_ids - new_ids - bridged
                if missing:
                    removed_by_bucket[bucket_label] = sorted(missing)

            # Also handle the case where a whole bucket disappeared from NEW
            # (e.g., a whole connection profile was deleted). Above loop
            # already covers this because the bucket key is in old_buckets
            # but new_buckets.get(...) returns empty -> all old_ids
            # surfaced (minus bridged).

            if not removed_by_bucket:
                continue

            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        removed_details=self._format_removed(removed_by_bucket),
                    ),
                    content_object=connector,
                )
            )
        return results

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _collect_param_ids(connector: Connector) -> Dict[str, Set[str]]:
        """Build ``{bucket_label: {field_id, ...}}`` for every param-bearing
        location on the connector.

        Bucket labels:
          - ``capability '<cap_id>'`` for each capability's unified
            configurations list (the parser already merges
            capabilities.yaml + configurations.yaml general_configurations
            and per-capability configurations into this list).
          - ``connection.yaml (general_configurations)`` for the flat
            connection-level general configs (if present).
          - ``connection.yaml (profile '<profile_id>')`` for each
            connection profile's configurations.
        """
        buckets: Dict[str, Set[str]] = {}

        # Capability buckets — unified general + per-cap configs.
        for cap in connector.capabilities:
            label = f"capability '{cap.id}'"
            field_ids: Set[str] = set()
            for group in cap.configurations:
                for field in group.fields:
                    field_ids.add(field.id)
            # Always record the bucket (even empty) so a previously-
            # populated capability that was emptied surfaces correctly
            # when diffed against the NEW empty bucket.
            buckets[label] = field_ids

        # Connection buckets — general + per-profile.
        if connector.connection is not None:
            if connector.connection.general_configurations is not None:
                label = "connection.yaml (general_configurations)"
                field_ids = set()
                for group in connector.connection.general_configurations.configurations:
                    for field in group.fields:
                        field_ids.add(field.id)
                buckets[label] = field_ids

            for profile in connector.connection.profiles:
                label = f"connection.yaml (profile '{profile.id}')"
                field_ids = set()
                for group in profile.configurations:
                    for field in group.fields:
                        field_ids.add(field.id)
                buckets[label] = field_ids

        return buckets

    @staticmethod
    def _collect_serializer_bridged_old_ids(connector: Connector) -> Set[str]:
        """Collect every old field id the NEW connector's handler
        serializers bridge via ``field_mappings.field_name``.

        Each serializer entry has shape ``{id: <new_id>, field_name:
        <old_id>}``. ``field_name`` is the original (pre-rename) id, so
        adding it to the bridged set forgives the apparent removal of
        that id in CO110's diff.

        This is the escape hatch that lets
        ``manifest_generator.dedup_field_id_and_register`` rename a field
        id (when two handlers collide) without tripping CO110, as long as
        the matching serializer entry is registered.
        """
        bridged: Set[str] = set()
        for handler in connector.handlers:
            if handler.serializer is None:
                continue
            for fm in handler.serializer.field_mappings:
                if fm.field_name:
                    bridged.add(fm.field_name)
        return bridged

    @staticmethod
    def _format_removed(removed_by_bucket: Dict[str, List[str]]) -> str:
        """Render the per-bucket removed-id map deterministically."""
        return "\n".join(
            f"  {bucket_label}: {ids}"
            for bucket_label, ids in sorted(removed_by_bucket.items())
        )
