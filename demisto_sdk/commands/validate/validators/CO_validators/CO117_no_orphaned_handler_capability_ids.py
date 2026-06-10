from __future__ import annotations

from typing import Iterable, List, Set

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Connector


class NoOrphanedHandlerCapabilityIdsValidator(BaseValidator[ContentTypes]):
    error_code = "CO117"
    description = (
        "Validates that every capability id referenced by a handler's "
        "capabilities[].id list is actually declared in the connector's "
        "capabilities.yaml (either as a top-level capability id or as a "
        "nested sub_capabilities[].id)."
    )
    rationale = (
        "Handlers are bound to capabilities purely by id match: a handler "
        "claims a capability id, and the platform routes that capability's "
        "execution to the claiming handler. If the claimed id is not declared "
        "in capabilities.yaml, the handler is unreachable — dead code that "
        "wastes review cycles, masks intent, and may indicate a deletion or "
        "rename was applied only partially. This validator catches per-id "
        "drift before it lands in the repo."
    )
    error_message = (
        "Connector '{connector_id}' has handler(s) claiming undeclared "
        "capability ids (declare them in capabilities.yaml or remove them "
        "from the handler):\n{handler_details}"
    )
    related_field = "capabilities"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Per-id strict check: a handler is invalid if ANY id it claims is
        not declared in the connector's capabilities.yaml.

        Algorithm:
          1. Build the connector's valid-id set: every top-level
             ``capabilities[].id`` plus every nested
             ``capabilities[].sub_capabilities[].id``.
          2. For each handler, collect the set of ids it claims via
             ``handler.capabilities[].id``.
          3. Compute the difference (claimed - declared). Any non-empty
             difference is reported per-handler, listing exactly which ids
             are unknown.
          4. All issues for a connector are merged into ONE ValidationResult
             with per-handler line items, matching the CO114/CO123 pattern.

        A handler with no ``capabilities[]`` entries is a no-op for this
        validator (it has nothing to claim) and is not reported here — a
        separate validator (e.g., CO118-style) would be the right place for
        "handler claims zero capabilities" checks if that ever becomes a rule.
        """
        results: List[ValidationResult] = []
        for connector in content_items:
            # Step 1: build the set of valid ids in this connector
            valid_ids: Set[str] = set()
            for cap in connector.capabilities:
                valid_ids.add(cap.id)
                for sub in cap.sub_capabilities:
                    valid_ids.add(sub.id)

            # Step 2-3: per-handler diff
            handler_issues: List[str] = []
            for handler in connector.handlers:
                claimed_ids = [c.id for c in handler.capabilities]
                if not claimed_ids:
                    # Nothing to validate; out of scope for CO117.
                    continue
                unknown_ids = [cid for cid in claimed_ids if cid not in valid_ids]
                if unknown_ids:
                    handler_issues.append(
                        f"handler '{handler.id}' claims undeclared "
                        f"capability id(s): {sorted(unknown_ids)} "
                        f"(declared in capabilities.yaml: "
                        f"{sorted(valid_ids) or '[]'})"
                    )

            if handler_issues:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            handler_details="\n".join(handler_issues),
                        ),
                        content_object=connector,
                    )
                )
        return results
