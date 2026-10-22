"""
Record the pylint-based xsoar-linter results for every golden case into golden.json.

golden.json is the reference ("golden") output that every xsoar-linter engine must reproduce exactly.
It is recorded from the current pylint implementation, so it reflects today's behavior, including quirks.

Usage (from the demisto-sdk repo root):
    python demisto_sdk/commands/xsoar_linter/tests/test_files/golden/record_golden.py

Only re-record when adding new samples or cases, and only with the pylint engine.
This script is deleted together with the pylint implementation.
"""

import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

GOLDEN_DIR = Path(__file__).resolve().parent
SAMPLES_DIR = GOLDEN_DIR / "samples"
GOLDEN_FILE = GOLDEN_DIR / "golden.json"
SDK_ROOT = GOLDEN_DIR.parents[5]
PYLINT_PLUGINS_DIR = (
    SDK_ROOT / "demisto_sdk" / "commands" / "pre_commit" / "resources" / "pylint_plugins"
)

# Same pattern as ERROR_AND_WARNING_CODE_PATTERN in xsoar_linter.py, with the object name split out.
FINDING_PATTERN = re.compile(
    r"^(?P<path>/[^:\n]+):(?P<line>\d+):(?P<col>\d+): (?P<code>[EW]\d+) (?P<obj>[^:]*): (?P<message>.*)$"
)
LINTER_ENV_KEYS = ("LONGRUNNING", "PY2", "is_script", "commands")

SUPPORT_LEVELS = [
    None,
    "base",
    "community",
    "developer",
    "partner",
    "certified partner",
    "xsoar",
    "unknown-level",
]
PY2_SAMPLES = [
    "py2_compatible.py",
    "py2_syntax.py",
    "xsoar_type_annotations.py",
    "commands_dict_dispatch.py",
    "base_print.py",
]


def make_settings(
    support: Optional[str] = "xsoar",
    is_script: bool = False,
    long_running: bool = False,
    py2: bool = False,
    commands: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "support": support,
        "is_script": is_script,
        "long_running": long_running,
        "py2": py2,
        "commands": commands or [],
    }


def make_case(sample: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    kind = "script" if settings["is_script"] else "integration"
    parts = [sample.removesuffix(".py"), kind, f"support={settings['support']}"]
    if settings["long_running"]:
        parts.append("long_running")
    if settings["py2"]:
        parts.append("py2")
    if settings["commands"]:
        parts.append(f"commands={'|'.join(settings['commands'])}")
    return {"id": ",".join(parts), "sample": sample, "settings": settings}


def build_cases() -> List[Dict[str, Any]]:
    samples = sorted(path.name for path in SAMPLES_DIR.glob("*.py"))
    cases = []

    # Every sample as an integration and as a script, with all checkers enabled.
    for sample in samples:
        cases.append(make_case(sample, make_settings(is_script=False)))
        cases.append(make_case(sample, make_settings(is_script=True)))

    # Which rules run at each support level.
    for support in SUPPORT_LEVELS:
        cases.append(
            make_case(
                "support_tiers.py",
                make_settings(support=support, commands=["missing-command"]),
            )
        )

    # Long running integrations may sleep.
    cases.append(make_case("base_sleep.py", make_settings(long_running=True)))
    cases.append(make_case("support_tiers.py", make_settings(long_running=True)))

    # Python 2 integrations.
    for sample in PY2_SAMPLES:
        cases.append(
            make_case(
                sample,
                make_settings(
                    py2=True,
                    commands=["py2-dict-command", "py2-if-command", "legacy-concat-command", "dict-a"],
                ),
            )
        )

    # Command implementation detection (E9010).
    cases.extend(
        [
            make_case(
                "commands_if_dispatch.py",
                make_settings(
                    commands=[
                        "eq-command",
                        "reversed-command",
                        "list-a",
                        "list-b",
                        "tuple-a",
                        "tuple-b",
                        "set-a",
                        "set-b",
                        "or-a",
                        "or-b",
                        "fetch-incidents",
                        "xdr-get-alert",
                        "static-fstring",
                        "alias-one",
                        "alias-two",
                        "not-equal-command",
                        "prefix-something",
                        "after-else",
                        "nested-in-else",
                        "outside-main",
                        "match-command",
                        "never-implemented",
                    ]
                ),
            ),
            make_case(
                "commands_dict_dispatch.py",
                make_settings(
                    commands=[
                        "dict-a",
                        "search-command",
                        "vendor-dict-b",
                        "static-dict-fstring",
                        "dict-value-only",
                        "dict-in-value",
                        "never-implemented",
                    ]
                ),
            ),
            make_case(
                "commands_api_module.py",
                make_settings(commands=["api-command-a", "api-command-b"]),
            ),
            make_case(
                "commands_api_module_plain_import.py",
                make_settings(commands=["api-command-a"]),
            ),
            make_case(
                "commands_function_name_variable.py",
                make_settings(commands=["first-value", "second-value"]),
            ),
            make_case(
                "clean_integration.py",
                make_settings(commands=["vendor-get-item"]),
            ),
            make_case(
                "clean_integration.py",
                make_settings(commands=["vendor-get-item", "vendor-missing-command"]),
            ),
            make_case(
                "empty_file.py",
                make_settings(commands=["some-command"]),
            ),
        ]
    )
    return cases


def build_env(settings: Dict[str, Any]) -> Dict[str, str]:
    """Mirror build_xsoar_linter_env_var() in xsoar_linter.py for the given settings."""
    env = {key: value for key, value in os.environ.items() if key not in LINTER_ENV_KEYS}
    if not settings["is_script"] and settings["long_running"]:
        env["LONGRUNNING"] = "True"
    if settings["py2"]:
        env["PY2"] = "True"
    env["is_script"] = str(settings["is_script"])
    if not settings["is_script"]:
        env["commands"] = ",".join(settings["commands"])
    # Only the plugins folder, so the results do not depend on a local content checkout.
    env["PYTHONPATH"] = str(PYLINT_PLUGINS_DIR)
    return env


def parse_findings(output: str) -> List[Dict[str, Any]]:
    findings = []
    for line in output.splitlines():
        if match := FINDING_PATTERN.match(line):
            findings.append(
                {
                    "line": int(match["line"]),
                    "col": int(match["col"]),
                    "code": match["code"],
                    "obj": match["obj"],
                    "message": match["message"],
                }
            )
    return sorted(findings, key=lambda f: (f["line"], f["col"], f["code"], f["message"]))


def run_pylint_engine(sample: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Run the current pylint-based xsoar-linter on one sample and return its normalized result."""
    from demisto_sdk.commands.xsoar_linter.xsoar_linter import build_xsoar_linter_command

    command = build_xsoar_linter_command(settings["support"])
    command.append(str(SAMPLES_DIR / sample))
    process = subprocess.run(
        command, capture_output=True, env=build_env(settings), timeout=120
    )
    return {
        "fails": process.returncode != 0,
        "findings": parse_findings(process.stdout.decode("utf-8")),
    }


def record_case(case: Dict[str, Any]) -> Dict[str, Any]:
    return {**case, "expected": run_pylint_engine(case["sample"], case["settings"])}


def main() -> None:
    sys.path.insert(0, str(SDK_ROOT))
    cases = build_cases()
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        recorded = list(executor.map(record_case, cases))
    GOLDEN_FILE.write_text(json.dumps(recorded, indent=2) + "\n")
    total_findings = sum(len(case["expected"]["findings"]) for case in recorded)
    print(f"Recorded {len(recorded)} cases with {total_findings} findings to {GOLDEN_FILE}")  # noqa: T201


if __name__ == "__main__":
    main()
