from __future__ import annotations

from typing import Dict, Iterable, List, Optional, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

# Field-shape state carried through the diff: just the field_type string.
# ``None`` means the field declared no `field_type` in that snapshot,
# which the schema allows (`ConnectorField.field_type: Optional[str]`).
# A transition None -> concrete type or concrete -> None counts as a
# change here, same as a type-to-type change: the platform's rendering
# and stored-value shape are entirely field-type-driven, so any move
# is destructive.
FieldTypeState = Optional[str]


class NoParamTypeChangedValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO178"
    description = (
        "Breaking-change check: no XSOAR-visible connector field may "
        "change its `field_type` between versions. The XSOAR-visible "
        "field surface per handler is produced by "
        "`Connector.visible_fields_for_handler(handler)` — a unified "
        "walker over ``connection.yaml`` (general_configurations + the "
        "profiles the handler auth-binds to), ``capabilities.yaml`` "
        "(general_configurations), and ``configurations.yaml`` (both "
        "parent-capability and grouped sub-capability entries). Only "
        "field ids present in BOTH versions are diffed; additions and "
        "removals are the concern of CO175 / other validators."
    )
    rationale = (
        "`field_type` drives both the FE rendering and the shape of "
        "the stored user value: flipping `input` -> `text_area`, "
        "`select` -> `multi_select`, `input` -> `checkbox`, etc., "
        "invalidates already-stored values for every enabled instance "
        "and rerenders the connection/configuration form in a shape "
        "that no longer matches what the user consented to. Fields may "
        "be added or removed (with the usual guards), but an existing "
        "field's type is a stable contract."
    )
    error_message = (
        "Handler '{handler_id}' has fields whose `field_type` changed "
        "between versions: {changes}."
    )
    related_field = "field_type"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Per-handler diff of `field_type` on XSOAR-visible fields.

        Only XSOAR handlers that exist in BOTH the old and the new
        version are diffed (matched by `handler.id`) — same policy as
        CO175/CO179. Fields absent from one side are skipped: those are
        CO175's concern.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            old_connector = cast(ContentTypes, connector.old_base_content_object)
            if old_connector is None:
                continue

            old_by_id = {h.id: h for h in old_connector.xsoar_handlers}

            for handler in connector.xsoar_handlers:
                old_handler = old_by_id.get(handler.id)
                if old_handler is None:
                    continue  # newly-added handler

                old_map = self._type_map(old_connector, old_handler)
                new_map = self._type_map(connector, handler)

                changed = self._changed_field_types(old_map, new_map)
                if not changed:
                    continue

                parts = [
                    f"{fid} ({old!r} → {new!r})"
                    for fid, (old, new) in sorted(changed.items())
                ]

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            handler_id=handler.id,
                            changes=", ".join(parts),
                        ),
                        content_object=connector,
                        path=handler.file_path,
                    )
                )

        return results

    # ------------------------------------------------------------------
    # Field-walk helpers (walker-based)
    # ------------------------------------------------------------------

    @staticmethod
    def _type_map(
        connector: ContentTypes,
        handler: HandlerData,
    ) -> Dict[str, FieldTypeState]:
        """Build ``{raw_field_id: field_type}`` for the XSOAR-visible field
        surface of a single handler.

        Delegates the field-walk to
        :meth:`Connector.visible_fields_for_handler` — the unified walker
        that aggregates ``connection.yaml`` (general_configurations +
        profiles), ``capabilities.yaml`` (general_configurations), and
        ``configurations.yaml`` (parent-capability and grouped sub-cap
        entries). Uses ``vf.raw_id`` (the field id as authored in the
        YAML, pre-serializer) because the diff invariant is on the
        author-owned identifier that survives across versions; the
        serializer's runtime rename is a separate concern.

        Duplicate raw ids across origins are collapsed by later-wins
        (dict assignment order). The invariant this validator asserts
        (type equality across versions) is symmetric across sources, so
        later-wins is safe: whichever origin the effective type comes
        from at runtime is the same origin both snapshots resolve
        through.
        """
        out: Dict[str, FieldTypeState] = {}
        for vf in connector.visible_fields_for_handler(handler):
            if vf.raw_id:
                out[vf.raw_id] = vf.field.field_type
        return out

    # ------------------------------------------------------------------
    # Diff logic
    # ------------------------------------------------------------------

    @staticmethod
    def _changed_field_types(
        old_map: Dict[str, FieldTypeState],
        new_map: Dict[str, FieldTypeState],
    ) -> Dict[str, tuple]:
        """Return ``{field_id: (old_type, new_type)}`` for field ids
        present in both maps whose `field_type` differs.

        No default-value exemption (unlike CO179): a type flip
        invalidates stored values structurally, so no runtime default
        substitution can rescue it — the fix is to declare a new field.
        """
        changed: Dict[str, tuple] = {}
        for fid, new_type in new_map.items():
            if fid not in old_map:
                continue  # newly-added field, not this validator's concern
            old_type = old_map[fid]
            if old_type != new_type:
                changed[fid] = (old_type, new_type)
        return changed
