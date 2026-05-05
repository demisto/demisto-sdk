from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Connector

XSOAR_MAINTAINER_TAG = "@xsoar-content"


class IsHandlerOwnershipFieldsAlignValidator(BaseValidator[ContentTypes]):
    error_code = "CO114"
    description = (
        "Validates that any handler claiming to be an XSOAR handler "
        "(module='xsoar') has its metadata.ownership block fully and correctly "
        "populated: team='xsoar' (exact lowercase) and maintainers contains "
        "'@xsoar-content' (exact case-sensitive)."
    )
    rationale = (
        "The is_xsoar property requires BOTH module=='xsoar' AND team=='xsoar' "
        "as an exact lowercase match. If only module is xsoar (case-mismatch on "
        "team, missing ownership block, or wrong maintainers), the handler is "
        "silently treated as non-xsoar by the platform, skipping XSOAR-only "
        "validators and behavior. This validator catches such misalignments "
        "with actionable error messages."
    )
    error_message = (
        "Connector '{connector_id}' has XSOAR handlers with ownership "
        "field issues:\n{handler_details}"
    )
    related_field = "metadata.ownership"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Check ownership field alignment for any handler with module='xsoar'.

        Iterates ALL handlers (not just connector.xsoar_handlers) because
        xsoar_handlers filters via is_xsoar, which requires the very alignment
        we're trying to verify — misaligned handlers would never appear there.

        For each handler whose module (case-insensitive) is 'xsoar', validate:
          R1. module is exactly 'xsoar' (lowercase) — case mismatch detected
              if module.lower() == 'xsoar' but module != 'xsoar'
          R2. metadata.ownership block is populated (not empty default)
          R3. team is exactly 'xsoar' (lowercase) — case mismatch detected if
              team.lower() == 'xsoar' but team != 'xsoar'
          R4. maintainers contains '@xsoar-content' (case-sensitive) — case
              mismatch detected if a case-insensitive match exists in the list

        If R2 fires (block missing), R3 and R4 are skipped to avoid noise.
        Otherwise R3 and R4 are independent — both can fire in the same handler.

        All issues for a connector are merged into ONE ValidationResult with
        per-handler line items.
        """
        results: List[ValidationResult] = []
        for connector in content_items:
            handler_issues: List[str] = []
            for handler in connector.handlers:
                # Trigger gate: only validate handlers claiming to be xsoar
                module = handler.module
                if module is None or module.lower() != "xsoar":
                    continue

                issues: List[str] = []

                # R1: module case sensitivity
                if module != "xsoar":
                    issues.append(
                        f"module='{module}' (case mismatch — must be exactly "
                        f"'xsoar' lowercase)"
                    )

                # R2: ownership block populated check
                ownership = handler.metadata.ownership
                ownership_is_empty_default = (
                    ownership.team == "" and not ownership.maintainers
                )
                if ownership_is_empty_default:
                    issues.append(
                        "missing the metadata.ownership block (must contain "
                        "team and maintainers)"
                    )
                else:
                    # R3: team case-sensitivity check (only if block exists)
                    team = handler.team
                    if team != "xsoar":
                        if team.lower() == "xsoar":
                            issues.append(
                                f"team='{team}' (case mismatch — must be "
                                f"exactly 'xsoar' lowercase)"
                            )
                        else:
                            issues.append(
                                f"team='{team}' (must be exactly 'xsoar')"
                            )

                    # R4: maintainers contains @xsoar-content
                    maintainers = ownership.maintainers
                    if XSOAR_MAINTAINER_TAG not in maintainers:
                        # Check for case-insensitive match
                        case_insensitive_match = any(
                            m.lower() == XSOAR_MAINTAINER_TAG.lower()
                            for m in maintainers
                        )
                        if case_insensitive_match:
                            issues.append(
                                f"missing '{XSOAR_MAINTAINER_TAG}' in "
                                f"maintainers (got: {maintainers}) — case "
                                f"mismatch detected, fix the case"
                            )
                        else:
                            issues.append(
                                f"missing '{XSOAR_MAINTAINER_TAG}' in "
                                f"maintainers (got: {maintainers})"
                            )

                if issues:
                    handler_issues.append(
                        f"handler '{handler.id}' - " + ", ".join(issues)
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
