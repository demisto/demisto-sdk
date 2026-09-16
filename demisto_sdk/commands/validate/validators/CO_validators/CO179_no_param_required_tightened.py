from __future__ import annotations

from typing import Dict, Iterable, List, Set, Tuple, cast

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

# Modifier "required" is Optional[bool]; treat None (not declared) as False,
# so any explicit True on a modifier that used to be missing/False counts as
# a tightening transition.
ModifierRequired = bool

# Field state carried through the diff: (create_required, edit_required,
# has_default). ``has_default`` is True iff the field declares an explicit
# ``options.default_value`` (presence semantics - ``None`` means "no default
# declared"; ``""`` / ``0`` / ``False`` count as declared defaults).
FieldRequiredState = Tuple[ModifierRequired, ModifierRequired, bool]


class NoParamRequiredTightenedValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO179"
    description = (
        "Breaking-change check: no XSOAR-relevant connector field may have "
        "its `options.create_modifiers.required` OR "
        "`options.edit_modifiers.required` transition from False (or unset) "
        "to True across versions. **Exemption:** if the new version declares "
        "an explicit `options.default_value`, the tightening is allowed - "
        "the platform substitutes the default for existing instances so the "
        "next save does not fail. The XSOAR-visible field surface is built "
        "per XSOAR handler from: connection.yaml general_configurations, the "
        "connection.yaml profiles this handler authenticates against, "
        "capabilities.yaml general_configurations, and the "
        "configurations.yaml entries unified into the handler's declared "
        "capabilities."
    )
    rationale = (
        "Making a previously-optional field required is a breaking change: "
        "existing enabled instances that never provided a value would fail "
        "validation on their next save, silently breaking upgrades. "
        "However, when the new field carries an explicit "
        "`options.default_value`, the platform substitutes the default at "
        "save time, so no upgrade path breaks - the tightening is safe. "
        "New fields may be introduced as required, and existing required "
        "fields may be relaxed to optional; the reverse transition without "
        "a default is not allowed."
    )
    error_message = (
        "Handler '{handler_id}' has fields whose `required` modifier "
        "tightened (was optional or unset, now required): {tightened}."
    )
    related_field = "options.create_modifiers.required,options.edit_modifiers.required"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Per-handler diff of the ``required`` modifier on XSOAR-visible fields.

        Only XSOAR handlers that exist in BOTH the old and the new version
        are diffed (matched by ``handler.id``). Fields absent from one side
        (added or removed) are skipped here - those are the concern of CO175
        (removal) / other validators; CO179 is strictly about a tightening
        transition on a field id that is present in both versions.
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

                old_map = self._required_map(old_connector, old_handler)
                new_map = self._required_map(connector, handler)

                tightened = self._tightened_fields(old_map, new_map)
                if not tightened:
                    continue

                # Deterministic message: sort by field id.
                parts = []
                for fid in sorted(tightened):
                    which = tightened[fid]
                    parts.append(f"{fid} ({'/'.join(sorted(which))})")

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            handler_id=handler.id,
                            tightened=", ".join(parts),
                        ),
                        content_object=connector,
                        path=handler.file_path,
                    )
                )

        return results

    # ------------------------------------------------------------------
    # Field-walk helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _required_pair(field: ConnectorField) -> FieldRequiredState:
        """Return ``(create_required, edit_required, has_default)`` for a field.

        - Missing modifier blocks and missing ``required`` keys both count as
          False (i.e. not required). Only an explicit True counts as required.
        - ``has_default`` follows presence semantics on
          ``options.default_value``: True iff the value is anything other
          than ``None`` (so ``""``, ``0``, ``False`` are all "declared").
          Rationale: any concrete default is what the platform will
          substitute for missing user input on upgrade, making a
          previously-optional -> now-required transition non-breaking.
        """
        opts = getattr(field, "options", None)
        if opts is None:
            return (False, False, False)
        create = getattr(opts, "create_modifiers", None)
        edit = getattr(opts, "edit_modifiers", None)
        create_req = bool(getattr(create, "required", False)) if create else False
        edit_req = bool(getattr(edit, "required", False)) if edit else False
        has_default = getattr(opts, "default_value", None) is not None
        return (create_req, edit_req, has_default)

    @classmethod
    def _required_map(
        cls,
        connector: ContentTypes,
        handler: HandlerData,
    ) -> Dict[str, FieldRequiredState]:
        """Build ``{field_id: (create_required, edit_required)}`` for the
        XSOAR-visible field surface of a single handler.

        Sources (mirrors ``ConnectorParser._collect_handler_fields``):
          1. connection.yaml general_configurations
          2. connection.yaml profiles used by handler.capabilities[].auth_options[].id
          3. capabilities.yaml general_configurations
             (from ``connector.capabilities_metadata.general_configurations``)
          4. per-capability configurations unified onto ``CapabilityData.configurations``
             for capabilities this handler declares
             (note: this ALSO includes the source-3 general block after parser
             unification, so it is naturally deduplicated by the dict.)

        Duplicate field ids across sources are collapsed by later-wins,
        which is fine for CO179: if the same id carries different modifiers
        across yamls, at least one place must satisfy the invariant. The
        source-4 (per-capability) view mirrors the effective runtime shape.
        """
        out: Dict[str, FieldRequiredState] = {}

        # 1. connection.yaml general_configurations
        conn = connector.connection
        if conn is not None and conn.general_configurations is not None:
            for group in conn.general_configurations.configurations:
                for f in group.fields:
                    if f and f.id:
                        out[f.id] = cls._required_pair(f)

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
                                out[f.id] = cls._required_pair(f)

        # 3. capabilities.yaml general_configurations
        cap_meta = connector.capabilities_metadata
        if cap_meta is not None and cap_meta.general_configurations is not None:
            for group in cap_meta.general_configurations.configurations:
                for f in group.fields:
                    if f and f.id:
                        out[f.id] = cls._required_pair(f)

        # 4. per-capability configurations (already unified by the parser)
        handler_cap_ids: Set[str] = {
            hc.id for hc in handler.capabilities if hc and hc.id
        }
        for cap in connector.capabilities:
            if cap.id in handler_cap_ids:
                for group in cap.configurations:
                    for f in group.fields:
                        if f and f.id:
                            out[f.id] = cls._required_pair(f)

        return out

    # ------------------------------------------------------------------
    # Diff logic
    # ------------------------------------------------------------------

    @staticmethod
    def _tightened_fields(
        old_map: Dict[str, FieldRequiredState],
        new_map: Dict[str, FieldRequiredState],
    ) -> Dict[str, Set[str]]:
        """Return ``{field_id: {"create", "edit"}}`` for fields whose
        create/edit ``required`` transitioned from False->True.

        Only field ids present in BOTH old and new are considered.

        Default-value exemption: when the NEW version of the field
        declares an explicit ``options.default_value`` (i.e.
        ``has_default`` is True on the new side), the field is exempt
        from the tightening check even if create/edit tightened. The
        platform substitutes the default for existing instances on
        save, so the tightening is non-breaking. The check consults the
        NEW side (not old) because the exemption is about how the
        upgraded connector treats existing instances at save time.
        """
        tightened: Dict[str, Set[str]] = {}
        for fid, (new_create, new_edit, new_has_default) in new_map.items():
            if fid not in old_map:
                continue  # newly-added field, not this validator's concern
            if new_has_default:
                # Exemption: platform will substitute the default on save.
                continue
            old_create, old_edit, _old_has_default = old_map[fid]
            which: Set[str] = set()
            if (not old_create) and new_create:
                which.add("create")
            if (not old_edit) and new_edit:
                which.add("edit")
            if which:
                tightened[fid] = which
        return tightened
