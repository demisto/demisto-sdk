"""Lint one integration/script file with the ast-based xsoar-linter checkers."""

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional

from demisto_sdk.commands.xsoar_linter.checkers.checker import run_checkers
from demisto_sdk.commands.xsoar_linter.checkers.context import (
    FileContext,
    parse_error_finding,
)
from demisto_sdk.commands.xsoar_linter.checkers.models import (
    Finding,
    LintResult,
    LintSettings,
)
from demisto_sdk.commands.xsoar_linter.checkers.pragmas import build_suppressions
from demisto_sdk.commands.xsoar_linter.checkers.registry import (
    all_rule_names,
    checkers_for_support_level,
    rules_for_checkers,
)

GOLDEN_SAMPLES_DIR = (
    Path(__file__).resolve().parent.parent
    / "tests"
    / "test_files"
    / "golden"
    / "samples"
)


def lint_source(source: str, module_name: str, settings: LintSettings) -> LintResult:
    """
    Lint python source code.

    The run fails when:
        * an error (E) finding was reported, or the file cannot be parsed,
        * the support level is unknown (no rules can be chosen),
        * the file has no statements and any finding was reported.
    """
    checker_classes = checkers_for_support_level(settings.support)
    if not checker_classes:
        return LintResult(findings=[], fails=True)

    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return LintResult(
            findings=[parse_error_finding(error, module_name)], fails=True
        )

    suppressions = build_suppressions(source, tree, all_rule_names())
    if suppressions.skip_file:
        return LintResult()

    context = FileContext(
        tree, settings, rules_for_checkers(checker_classes), suppressions
    )
    run_checkers(context, [checker_class(context) for checker_class in checker_classes])

    findings = sorted(set(context.findings), key=Finding.sort_key)
    has_error = any(finding.code.startswith("E") for finding in findings)
    empty_module_with_findings = not tree.body and bool(findings)
    return LintResult(findings=findings, fails=has_error or empty_module_with_findings)


def lint_file(file_path: Path, settings: LintSettings) -> LintResult:
    source = file_path.read_text(encoding="utf-8")
    return lint_source(source, file_path.stem, settings)


def format_finding(file_path: Path, finding: Finding) -> str:
    """The same line format the hook and GitHub annotations parse: path:line:col: CODE obj: message"""
    return (
        f"{file_path.resolve()}:{finding.line}:{finding.col}: "
        f"{finding.code} {finding.obj}: {finding.message}"
    )


def settings_from_integration_script(integration_script: Any) -> LintSettings:
    """Build lint settings from an Integration or Script content object."""
    from packaging.version import Version

    from demisto_sdk.commands.content_graph.objects import Integration, Script

    is_integration = isinstance(integration_script, Integration)
    python_version: Optional[str] = integration_script.python_version
    commands: List[str] = (
        [command.name for command in integration_script.commands]
        if is_integration
        else []
    )
    return LintSettings(
        support=integration_script.support,
        is_script=isinstance(integration_script, Script),
        long_running=bool(is_integration and integration_script.long_running),
        py2=bool(python_version and Version(python_version).major < 3),
        commands=commands,
    )


def run_golden_case(sample: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Run one golden test case. `sample` is a file name in the golden samples folder."""
    result = lint_file(GOLDEN_SAMPLES_DIR / sample, LintSettings(**settings))
    return {
        "fails": result.fails,
        "findings": [finding.to_dict() for finding in result.findings],
    }
