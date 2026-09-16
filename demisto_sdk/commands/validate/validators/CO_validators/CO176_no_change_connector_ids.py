from __future__ import annotations

from typing import Dict, Iterable, List, Set, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class NoChangeConnectorIDsValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO176"
    description = (
        "Breaking-change check: no id in any of the six id families "
        "(connector_id, handler_id, capability_id, sub_capability_id, "
        "profile_id, view_group_id) that existed in the prior version of "
        "the connector may be renamed or removed in the new version. "
        "Additions are allowed - the prior set must be a subset of the new "
        "set for every family. For non-grouped connectors, ``view_group_id`` "
        "is naturally empty on both sides and never triggers."
    )
    rationale = (
        "These ids are the identity keys that enabled instances, references, "
        "and downstream automations rely on to locate handlers, capabilities, "
        "auth profiles, and the connector itself. Renaming or removing any "
        "of them silently invalidates persisted state and breaks upgrades."
    )
    error_message = (
        "Connector '{connector_id}' renamed or removed ids that existed in "
        "the prior version: {problems}."
    )
    related_field = "id"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """One aggregated result per connector.

        Compare the 5 id-families as sets. Anything in the prior set but not
        in the new set is a rename-or-removal breaking change (union: prior
        must be a subset of new).
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            old_connector = cast(ContentTypes, connector.old_base_content_object)
            if old_connector is None:
                continue

            problems = self._diff(old_connector, connector)
            if not problems:
                continue

            problem_str = "; ".join(
                f"{family}: missing {sorted(ids)!r}" for family, ids in problems.items()
            )
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        problems=problem_str,
                    ),
                    content_object=connector,
                    path=connector.path,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Diff helpers
    # ------------------------------------------------------------------

    def _diff(
        self,
        old_connector: ContentTypes,
        new_connector: ContentTypes,
    ) -> Dict[str, Set[str]]:
        """Return ``{family: {ids missing in the new version}}`` for every
        family that has at least one missing id."""
        families = {
            "connector_id": (
                self._connector_id_set(old_connector),
                self._connector_id_set(new_connector),
            ),
            "handler_id": (
                self._handler_ids(old_connector),
                self._handler_ids(new_connector),
            ),
            "capability_id": (
                self._capability_ids(old_connector),
                self._capability_ids(new_connector),
            ),
            "sub_capability_id": (
                self._sub_capability_ids(old_connector),
                self._sub_capability_ids(new_connector),
            ),
            "profile_id": (
                self._profile_ids(old_connector),
                self._profile_ids(new_connector),
            ),
            "view_group_id": (
                self._view_group_ids(old_connector),
                self._view_group_ids(new_connector),
            ),
        }
        return {
            family: (old - new) for family, (old, new) in families.items() if old - new
        }

    @staticmethod
    def _connector_id_set(connector: ContentTypes) -> Set[str]:
        """Wrap the single top-level id in a set for uniform handling."""
        if connector.object_id:
            return {connector.object_id}
        return set()

    @staticmethod
    def _handler_ids(connector: ContentTypes) -> Set[str]:
        return {h.id for h in (connector.handlers or []) if h and h.id}

    @staticmethod
    def _capability_ids(connector: ContentTypes) -> Set[str]:
        return {c.id for c in (connector.capabilities or []) if c and c.id}

    @staticmethod
    def _sub_capability_ids(connector: ContentTypes) -> Set[str]:
        ids: Set[str] = set()
        for cap in connector.capabilities or []:
            if not cap:
                continue
            for sub in cap.sub_capabilities or []:
                if sub and sub.id:
                    ids.add(sub.id)
        return ids

    @staticmethod
    def _profile_ids(connector: ContentTypes) -> Set[str]:
        if not connector.connection:
            return set()
        return {p.id for p in (connector.connection.profiles or []) if p and p.id}

    @staticmethod
    def _view_group_ids(connector: ContentTypes) -> Set[str]:
        """Return the set of ``connection.view_groups[].id``.

        Grouped connectors declare view_groups that field bindings reference
        by id; renaming or removing one silently orphans bindings and breaks
        the rendered form. Non-grouped connectors leave this list empty on
        both sides so the family never triggers for them.
        """
        if not connector.connection:
            return set()
        return {
            vg.id for vg in (connector.connection.view_groups or []) if vg and vg.id
        }
