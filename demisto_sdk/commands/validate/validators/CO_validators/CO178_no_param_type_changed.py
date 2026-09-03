from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    ConnectorField,
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
        "field surface per handler is built from: connection.yaml "
        "general_configurations, the connection.yaml profiles this "
        "handler authenticates against, capabilities.yaml "
        "general_configurations, and the configurations.yaml entries "
        "unified into the handler's declared capabilities — same walk "
        "as CO179. Only field ids present in BOTH versions are diffed; "
        "additions and removals are the concern of CO175 / other "
        "validators."
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
    # Field-walk helpers (mirror CO179's field-surface walker)
    # ------------------------------------------------------------------

    @staticmethod
    def _field_type(field: ConnectorField) -> FieldTypeState:
        """Return the `field_type` string, or ``None`` when the field
        declares no explicit type. Preserves the None/concrete
        distinction so any transition is detected — see the module-level
        note on ``FieldTypeState``.
        """
        return getattr(field, "field_type", None)

    @classmethod
    def _type_map(
        cls,
        connector: ContentTypes,
        handler: HandlerData,
    ) -> Dict[str, FieldTypeState]:
        """Build ``{field_id: field_type}`` for the XSOAR-visible field
        surface of a single handler.

        Sources (mirrors CO179's ``_required_map`` and, upstream,
        ``ConnectorParser._collect_handler_fields``):
          1. connection.yaml general_configurations
          2. connection.yaml profiles used by handler.capabilities[].auth_options[].id
          3. capabilities.yaml general_configurations
          4. per-capability configurations unified onto CapabilityData.configurations
             for capabilities this handler declares

        Duplicate field ids across sources are collapsed by later-wins,
        matching CO179's semantics. The invariant this validator asserts
        (type equality across versions) is symmetric across sources, so
        later-wins is safe: whichever source the effective type comes
        from at runtime is the same source both snapshots resolve
        through.
        """
        out: Dict[str, FieldTypeState] = {}

        # 1. connection.yaml general_configurations
        conn = connector.connection
        if conn is not None and conn.general_configurations is not None:
            for group in conn.general_configurations.configurations:
                for f in group.fields:
                    if f and f.id:
                        out[f.id] = cls._field_type(f)

        # 2. connection.yaml profiles used by this handler
        auth_profile_ids: Set[str] = {
            ao.id
            for hc in handler.capabilities
            for ao in hc.auth_options
            if ao and ao.id
        }
        if conn is not None:
            for profile in conn.profiles:
                if profile.id in auth_profile_ids:
                    for group in profile.configurations:
                        for f in group.fields:
                            if f and f.id:
                                out[f.id] = cls._field_type(f)

        # 3. capabilities.yaml general_configurations
        cap_meta = connector.capabilities_metadata
        if cap_meta is not None and cap_meta.general_configurations is not None:
            for group in cap_meta.general_configurations.configurations:
                for f in group.fields:
                    if f and f.id:
                        out[f.id] = cls._field_type(f)

        # 4. per-capability configurations (already unified by the parser)
        handler_cap_ids: Set[str] = {
            hc.id for hc in handler.capabilities if hc and hc.id
        }
        for cap in connector.capabilities:
            if cap.id in handler_cap_ids:
                for group in cap.configurations:
                    for f in group.fields:
                        if f and f.id:
                            out[f.id] = cls._field_type(f)

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
