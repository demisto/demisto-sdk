from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

# The action whose return_data cardinality this validator enforces.
SHOW_CLASSIFIER_ACTION = "show_classifier"

# A show_classifier action must reference EXACTLY ONE classifier field.
EXPECTED_RETURN_DATA_COUNT = 1


class IsShowClassifierSingleReturnDataValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO196"
    description = (
        "Validates that every 'show_classifier' action declares EXACTLY ONE "
        "return_data entry (the single classifier field it surfaces)."
    )
    rationale = (
        "The 'show_classifier' action surfaces the instance's configured "
        "classifier field. It references that field through its 'return_data' "
        "list, which must name exactly one classifier field: an empty (or "
        "missing) return_data points at nothing, while two or more entries "
        "are ambiguous about which field the action displays. Enforcing a "
        "single return_data entry keeps the classifier surface unambiguous. "
        "This rule is independent of CO195 (which checks the action exists and "
        "references the delivered classifier id) and CO161 (required fetch "
        "actions); CO196 only constrains return_data cardinality on "
        "'show_classifier' actions wherever they appear."
    )
    error_message = (
        "Handler '{handler_id}' has 'show_classifier' action(s) with an "
        "invalid return_data cardinality: {problems}. Exactly one classifier "
        "field is expected per action."
    )
    related_field = "capabilities[].actions"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """For every XSOAR handler, every capability, and every action of type
        ``show_classifier``, verify the action's ``return_data`` contains
        EXACTLY ONE element. Flag both empty/missing (0 entries) and multiple
        (2+ entries).

        Per-handler aggregated result (one row per handler, listing every
        offending action). Path points at the offending ``handler.yaml``.
        Actions of other types are ignored (the rule only applies to
        ``show_classifier``).
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.xsoar_handlers:
                problems: List[str] = []
                for cap in handler.capabilities:
                    for action in cap.actions:
                        if not action or action.type != SHOW_CLASSIFIER_ACTION:
                            continue
                        count = len(action.return_data or [])
                        if count != EXPECTED_RETURN_DATA_COUNT:
                            problems.append(
                                f"capability '{cap.id}' has a "
                                f"'{SHOW_CLASSIFIER_ACTION}' action whose "
                                f"return_data has {count} entr"
                                f"{'y' if count == 1 else 'ies'} "
                                f"({sorted(action.return_data or []) or '[]'})"
                            )

                if problems:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                handler_id=handler.id,
                                problems="; ".join(problems),
                            ),
                            content_object=connector,
                            path=handler.file_path,
                        )
                    )

        return results
