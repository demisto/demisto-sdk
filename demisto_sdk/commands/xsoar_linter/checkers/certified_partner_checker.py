"""Rules for certified partner support level and above. Rule logic is added in Step 3."""

from typing import ClassVar, List

from demisto_sdk.commands.xsoar_linter.checkers.checker import Checker
from demisto_sdk.commands.xsoar_linter.checkers.models import Rule


class CertifiedPartnerChecker(Checker):
    RULES: ClassVar[List[Rule]] = [
        Rule("E9001", "sys-exit-exists", "Sys.exit use is found, Please use return instead."),
        Rule("W9005", "main-func-doesnt-exist", "Main function wasnt found in the file, Please add main()"),
        Rule(
            "W9008",
            "demisto-results-exists",
            "Do not use demisto.results function. Please return CommandResults object instead.",
        ),
        Rule(
            "W9009",
            "return-outputs-exists",
            "Do not use return_outputs function. Please return CommandResults object instead.",
        ),
        Rule(
            "W9016",
            "init-params-outside-main",
            "Initialize of params was found outside of main function. Please use demisto.params() only inside main func",
        ),
        Rule(
            "W9017",
            "init-args-outside-main",
            "Initialize of args was found outside of main function. Please use demisto.args() only inside main func",
        ),
    ]
