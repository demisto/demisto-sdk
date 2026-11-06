"""Which checkers run for each support level."""

from typing import Dict, List, Optional, Type

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.xsoar_linter.checkers.base_checker import BaseChecker
from demisto_sdk.commands.xsoar_linter.checkers.certified_partner_checker import (
    CertifiedPartnerChecker,
)
from demisto_sdk.commands.xsoar_linter.checkers.checker import Checker
from demisto_sdk.commands.xsoar_linter.checkers.models import Rule
from demisto_sdk.commands.xsoar_linter.checkers.partner_checker import PartnerChecker
from demisto_sdk.commands.xsoar_linter.checkers.xsoar_checker import XsoarChecker

DEFAULT_SUPPORT_LEVEL = "base"
CHECKERS_BY_SUPPORT_LEVEL: Dict[str, List[Type[Checker]]] = {
    "base": [BaseChecker],
    "community": [BaseChecker],
    "developer": [BaseChecker],
    "partner": [BaseChecker, PartnerChecker],
    "certified partner": [BaseChecker, PartnerChecker, CertifiedPartnerChecker],
    "xsoar": [BaseChecker, PartnerChecker, CertifiedPartnerChecker, XsoarChecker],
}
ALL_CHECKERS: List[Type[Checker]] = CHECKERS_BY_SUPPORT_LEVEL["xsoar"]


def checkers_for_support_level(support_level: Optional[str]) -> List[Type[Checker]]:
    """
    The checkers to run for a support level. An unknown level logs a warning and runs no checkers.
    """
    support_level = support_level or DEFAULT_SUPPORT_LEVEL
    checkers = CHECKERS_BY_SUPPORT_LEVEL.get(support_level)
    if checkers is None:
        logger.warning(
            f"Integration support level: '{support_level}' is not valid. "
            f"Known values: {', '.join(CHECKERS_BY_SUPPORT_LEVEL)}."
        )
        return []
    return checkers


def all_rule_names() -> Dict[str, str]:
    """Maps every rule code and symbol to its code, for reading disable comments."""
    names: Dict[str, str] = {}
    for checker in ALL_CHECKERS:
        for rule in checker.RULES:
            names[rule.code] = rule.code
            names[rule.symbol] = rule.code
    return names


def rules_for_checkers(checkers: List[Type[Checker]]) -> Dict[str, Rule]:
    return {rule.code: rule for checker in checkers for rule in checker.RULES}
