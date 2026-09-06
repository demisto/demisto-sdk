from __future__ import annotations

from typing import Dict, Iterable, List, Set, Tuple, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerAuthMethod,
    HandlerData,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class NoRemovedAuthOptionValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO181"
    description = (
        "Breaking-change check: no `auth_options[].id` or "
        "`auth_options[].methods[].id` present in the prior version of an "
        "XSOAR handler may be removed. Scoping: auth-option ids are diffed "
        "per (handler_id, capability_id); method ids are diffed per "
        "(handler_id, capability_id, auth_option_id). Renames count as "
        "removals; newly-added ids are allowed."
    )
    rationale = (
        "Removing an auth option or auth method that existed in a prior "
        "release is a breaking change: enabled instances that authenticated "
        "via that option/method would lose their auth path on upgrade and "
        "fail to reconnect. New options/methods may be added, but existing "
        "ones must be preserved for the instance-migration story to hold."
    )
    error_message = (
        "Handler '{handler_id}' removed auth references that existed in the "
        "prior version: {removed}."
    )
    related_field = "capabilities.auth_options"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Per-handler diff of auth_options and their methods.

        Only XSOAR handlers that exist in BOTH the old and the new version
        are diffed (matched by ``handler.id``). Removed handlers as a whole
        are not this validator's concern (CO176 `handler_id` family covers
        that); we only inspect handlers whose id survives.
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

                removed_parts = self._removed_parts(old_handler, handler)
                if not removed_parts:
                    continue

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            handler_id=handler.id,
                            removed="; ".join(removed_parts),
                        ),
                        content_object=connector,
                        path=handler.file_path,
                    )
                )

        return results

    # ------------------------------------------------------------------
    # Diff helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _method_id(method) -> str:
        """Normalize an auth method entry (str | HandlerAuthMethod) to its id."""
        if isinstance(method, HandlerAuthMethod):
            return method.id or ""
        if isinstance(method, str):
            return method
        # Defensive: pydantic may hand us an unmodelled dict during edge parses.
        if isinstance(method, dict):
            return str(method.get("id") or "")
        return ""

    @classmethod
    def _auth_options_map(
        cls,
        handler: HandlerData,
    ) -> Tuple[Dict[str, Set[str]], Dict[Tuple[str, str], Set[str]]]:
        """Return two maps for a single handler:

        * ``by_cap``: ``{capability_id: {auth_option_id, ...}}``
        * ``by_ao``: ``{(capability_id, auth_option_id): {method_id, ...}}``

        Both are derived from ``handler.capabilities[].auth_options[]``.
        """
        by_cap: Dict[str, Set[str]] = {}
        by_ao: Dict[Tuple[str, str], Set[str]] = {}
        for cap in handler.capabilities:
            if not cap or not cap.id:
                continue
            cap_bucket = by_cap.setdefault(cap.id, set())
            for ao in cap.auth_options:
                if not ao or not ao.id:
                    continue
                cap_bucket.add(ao.id)
                method_ids = {
                    mid
                    for mid in (cls._method_id(m) for m in (ao.methods or []))
                    if mid
                }
                by_ao[(cap.id, ao.id)] = method_ids
        return by_cap, by_ao

    @classmethod
    def _removed_parts(
        cls,
        old_handler: HandlerData,
        new_handler: HandlerData,
    ) -> List[str]:
        """Return sorted human-readable parts describing removed auth
        options / methods on ``new_handler`` vs ``old_handler``.
        """
        old_by_cap, old_by_ao = cls._auth_options_map(old_handler)
        new_by_cap, new_by_ao = cls._auth_options_map(new_handler)

        parts: List[str] = []

        # Removed auth_option ids per (handler, capability).
        # Only compare on capability ids that exist in BOTH versions - if the
        # capability itself was dropped, CO176 flags that at the capability_id
        # family; CO181 stays focused on per-cap auth-option shape.
        for cap_id in sorted(set(old_by_cap) & set(new_by_cap)):
            removed_aos = old_by_cap[cap_id] - new_by_cap[cap_id]
            if removed_aos:
                joined = ", ".join(repr(x) for x in sorted(removed_aos))
                parts.append(f"capability {cap_id!r} removed auth_option(s): {joined}")

        # Removed method ids per (handler, capability, auth_option).
        # Only compare on (cap_id, ao_id) present in BOTH versions - a whole
        # auth_option removal is already reported above; here we drill into
        # method-level removals on surviving auth options.
        shared_ao_keys = set(old_by_ao) & set(new_by_ao)
        for cap_id, ao_id in sorted(shared_ao_keys):
            removed_methods = old_by_ao[(cap_id, ao_id)] - new_by_ao[(cap_id, ao_id)]
            if removed_methods:
                joined = ", ".join(repr(x) for x in sorted(removed_methods))
                parts.append(
                    f"capability {cap_id!r} auth_option {ao_id!r} "
                    f"removed method(s): {joined}"
                )

        return parts
