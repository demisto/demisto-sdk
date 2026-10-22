"""Rules for partner support level and above. Rule logic is added in Step 3."""

from typing import ClassVar, List

from demisto_sdk.commands.xsoar_linter.checkers.checker import Checker
from demisto_sdk.commands.xsoar_linter.checkers.models import Rule


class PartnerChecker(Checker):
    RULES: ClassVar[List[Rule]] = [
        Rule(
            "W9010",
            "try-except-main-doesnt-exists",
            "try and except statements were not found in main function. Please add them",
        ),
        Rule(
            "W9011",
            "too-many-return-error",
            "return_error used too many times, should be used only once in the code, in main function. "
            "Please remove other usages.",
        ),
        Rule(
            "W9012",
            "return-error-does-not-exist-in-main",
            "return_error should be used in main function. Please add it.",
        ),
    ]
