"""Rules for xsoar support level. Rule logic is added in Step 3."""

from typing import ClassVar, List

from demisto_sdk.commands.xsoar_linter.checkers.checker import Checker
from demisto_sdk.commands.xsoar_linter.checkers.models import Rule


class XsoarChecker(Checker):
    RULES: ClassVar[List[Rule]] = [
        Rule(
            "W9014",
            "missing-arg-type-annoation",
            "Function arguments are missing type annotations. Please add type annotations",
        ),
        Rule(
            "W9018",
            "not-implemented-error-doesnt-exist",
            "It is best practice for Integrations to raise a NotImplementedError when receiving a command which is "
            "not recognized. exception",
        ),
        Rule(
            "W9019",
            "direct-access-args-params-dict-exist",
            "It is best practice to use .get when accessing the arg/params dict object rather then direct access.",
        ),
    ]
