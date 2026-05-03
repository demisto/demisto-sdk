import os

os.environ["DEMISTO_SDK_IGNORE_CONTENT_WARNING"] = "True"
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
import yaml

from demisto_sdk.commands.common.logger import logger, logging_setup

main = typer.Typer()


COMMAND_TO_CAPABILITY: Dict[str, str] = {
    "fetch-incidents": "Fetch Issues",
    "fetch-events": "Log Collection",
    "fetch-credentials": "Fetch Secrets",
    "fetch-indicators": "Threat Intelligence & Enrichment",
    "fetch-assets": "Fetch Assets and Vulnerabilities",
}

EXCLUDED_AUTOMATION_PATTERNS: List[str] = [
    "get-indicators",
    "get-events",
    "fetch-incidents",
    "fetch-events",
    "fetch-credentials",
]


# ---------------------------------------------------------------------------
# Step 1: Decide capabilities
# ---------------------------------------------------------------------------
def _is_pure_event_collector(integration_yml: dict) -> bool:
    """Check whether the integration is a pure event collector with no other fetch capabilities.

    Returns True only if the integration has isfetchevents but NO other fetch indicators
    (no isfetch, no isfetch:platform, no feed, no isfetchassets, no isFetchCredentials param).
    Used to gate Rule 2's early-exit so multi-purpose collectors don't drop their other capabilities.
    """
    script = integration_yml.get("script", {}) or {}
    if script.get("isfetch"):
        return False
    if script.get("isfetch:platform"):
        return False
    if script.get("feed"):
        return False
    if script.get("isfetchassets"):
        return False
    # Check for isFetchCredentials param
    for param in integration_yml.get("configuration", []) or []:
        if param.get("name") == "isFetchCredentials":
            return False
    return True


def decide_capabilities(integration_yml: dict) -> Dict[str, List[str]]:
    """Decide which capabilities should be created from the integration YML.

    Implements the rules listed in the task description. The function may
    early-exit returning a minimal mapping when one of the early-exit
    conditions for ``Log Collection`` or ``Threat Intelligence & Enrichment``
    is met.
    """
    result: Dict[str, List[str]] = {"general_configurations": []}

    integration_name: str = (integration_yml.get("name") or "").lower()
    script: dict = integration_yml.get("script") or {}
    configuration: List[dict] = integration_yml.get("configuration") or []
    commands: List[dict] = script.get("commands") or []
    command_names: List[str] = [c.get("name", "") for c in commands]

    # Rule 1 - Fetch Secrets
    if any(p.get("name") == "isFetchCredentials" for p in configuration):
        result["Fetch Secrets"] = []

    # Rule 2 - Log Collection (with possible early exit)
    if script.get("isfetchevents") is True:
        result["Log Collection"] = []
        get_events_cmd_count = sum(1 for n in command_names if "get-events" in n)
        if (
            "eventcollector" in integration_name or get_events_cmd_count == 1
        ) and _is_pure_event_collector(integration_yml):
            # Pure event collector — short-circuit to keep the result minimal
            return {"general_configurations": [], "Log Collection": []}

    # Rule 3 - Fetch Issues
    if script.get("isfetch") is True and script.get("isfetch:platform") is not False:
        result["Fetch Issues"] = []

    # Rule 4 - Threat Intelligence & Enrichment (with possible early exit)
    if script.get("feed") is True:
        result["Threat Intelligence & Enrichment"] = []
        get_indicators_cmd_count = sum(
            1 for n in command_names if "get-indicators" in n
        )
        if "feed" in integration_name or get_indicators_cmd_count == 1:
            return {
                "general_configurations": [],
                "Threat Intelligence & Enrichment": [],
            }

    # Rule 5 - Fetch Assets and Vulnerabilities
    if script.get("isfetchassets") is True:
        result["Fetch Assets and Vulnerabilities"] = []

    # Rule 6 - Automation
    for name in command_names:
        if not any(pattern in name for pattern in EXCLUDED_AUTOMATION_PATTERNS):
            result["Automation"] = []
            break

    return result


# ---------------------------------------------------------------------------
# Step 2: Map params to capabilities
# ---------------------------------------------------------------------------
def _handle_test_module(
    result: Dict[str, List[str]],
    command_params: dict,
    param_defaults: dict,
) -> None:
    """Step 2.1 - Add params from ``test-module`` without a default to
    ``general_configurations``."""
    commands_section: dict = command_params.get("commands") or {}
    test_module_params: List[str] = commands_section.get("test-module", []) or []
    for param in test_module_params:
        if (
            param not in param_defaults
            and param not in result["general_configurations"]
        ):
            result["general_configurations"].append(param)


def _apply_manual_mapping(
    result: Dict[str, List[str]],
    command_params: dict,
    manual_command_to_capability: Dict[str, List[str]],
) -> set:
    """Step 2.1.5 — Apply manual command-to-capability overrides.

    Manual mapping is the source of truth for any listed command. For each entry:
      1. Ensure each listed capability exists in the result dict (create with []).
      2. Add the command's params (from command_params['commands'][cmd]) to each
         listed capability.

    Returns the set of command names that were handled here, so subsequent steps
    (2.2 / 2.3) can skip them and avoid double-routing.

    No-op when ``manual_command_to_capability`` is empty.
    """
    handled_commands: set = set()
    if not manual_command_to_capability:
        return handled_commands

    commands_section: dict = command_params.get("commands") or {}
    for cmd_name, capability_list in manual_command_to_capability.items():
        # Ensure each capability exists.
        for cap in capability_list:
            if cap not in result:
                result[cap] = []
        # Route this command's params to each listed capability.
        params = commands_section.get(cmd_name) or []
        for cap in capability_list:
            for param in params:
                if param not in result[cap]:
                    result[cap].append(param)
        handled_commands.add(cmd_name)
    return handled_commands


def _single_capability_shortcut(
    result: Dict[str, List[str]],
    command_params: dict,
    handled_commands: Optional[set] = None,
) -> None:
    """Step 2.2 - When only a single (non-general) capability exists, dump all
    unique command params (excluding those already placed in
    ``general_configurations`` and those handled by manual mapping) into that
    capability."""
    handled_commands = handled_commands or set()
    target_capability = next(
        cap for cap in result.keys() if cap != "general_configurations"
    )
    already_placed = set(result["general_configurations"])
    seen: set = set()
    commands_section: dict = command_params.get("commands") or {}
    for cmd_name, params in commands_section.items():
        if cmd_name in handled_commands:
            continue
        for param in params or []:
            if param in already_placed or param in seen:
                continue
            seen.add(param)
            result[target_capability].append(param)


def _resolve_target_capability(cmd_name: str, result: Dict[str, List[str]]) -> str:
    """Decide which capability a command's params should be routed to.

    Resolution order:
    1. Exact match in ``COMMAND_TO_CAPABILITY`` (e.g. ``"fetch-events"`` →
       ``"Log Collection"``).
    2. Substring routing:
       - If ``"get-events"`` in command name AND ``"Log Collection"`` exists
         in the capabilities → ``"Log Collection"``.
       - If ``"get-indicators"`` in command name AND
         ``"Threat Intelligence & Enrichment"`` exists in the capabilities →
         ``"Threat Intelligence & Enrichment"``.
    3. Fallback: ``"Automation"``.
    """
    if cmd_name in COMMAND_TO_CAPABILITY:
        return COMMAND_TO_CAPABILITY[cmd_name]
    if "get-events" in cmd_name and "Log Collection" in result:
        return "Log Collection"
    if "get-indicators" in cmd_name and "Threat Intelligence & Enrichment" in result:
        return "Threat Intelligence & Enrichment"
    return "Automation"


def _multi_capability_mapping(
    result: Dict[str, List[str]],
    command_params: dict,
    handled_commands: Optional[set] = None,
) -> None:
    """Step 2.3 - For each command, map its params to the matching capability
    (or ``Automation``).  Skips test-module (handled in 2.1) and any command
    already routed by manual mapping (Step 2.1.5).  Warns if the target
    capability is missing from the result mapping."""
    handled_commands = handled_commands or set()
    commands_section: dict = command_params.get("commands") or {}
    for cmd_name, params in commands_section.items():
        if cmd_name == "test-module":
            # already handled in step 2.1
            continue
        if cmd_name in handled_commands:
            # already handled in step 2.1.5 (manual mapping)
            continue
        target = _resolve_target_capability(cmd_name, result)
        for param in params or []:
            if target in result:
                if param not in result[target]:
                    result[target].append(param)
            else:
                logger.warning(
                    f"{param} failed to add to {target} because it doesn't "
                    f"exist although it's a part of {cmd_name}."
                )


def _deduplicate(result: Dict[str, List[str]]) -> None:
    """Step 2.4 - Move any param appearing in two or more capabilities (or in
    ``general_configurations`` plus another capability) into
    ``general_configurations`` exactly once."""
    # Count occurrences of every param across all keys.
    occurrences: Dict[str, int] = {}
    for params in result.values():
        for param in params:
            occurrences[param] = occurrences.get(param, 0) + 1

    duplicated = {p for p, count in occurrences.items() if count >= 2}
    if not duplicated:
        return

    if "general_configurations" not in result:
        result["general_configurations"] = []

    for capability in list(result.keys()):
        result[capability] = [p for p in result[capability] if p not in duplicated]

    for param in duplicated:
        if param not in result["general_configurations"]:
            result["general_configurations"].append(param)


def _log_orphans(result: Dict[str, List[str]], param_defaults: dict) -> None:
    """Step 2.5 - Log any params present in ``param_defaults`` that ended up
    not being mapped to any capability."""
    placed: set = set()
    for params in result.values():
        placed.update(params)
    orphans = [p for p in param_defaults.keys() if p not in placed]
    if orphans:
        logger.warning(
            f"The following params are in param_defaults but were not mapped "
            f"to any capability: {orphans}"
        )


def map_params_to_capabilities(
    capabilities: Dict[str, List[str]],
    command_params: dict,
    param_defaults: dict,
    manual_command_to_capability: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, List[str]]:
    """Apply Step 2 - populate the capabilities mapping with parameter names
    derived from the supplied ``command_params`` and ``param_defaults`` JSON
    inputs. ``manual_command_to_capability`` (optional) overrides automatic
    routing for any listed commands."""
    manual_command_to_capability = manual_command_to_capability or {}

    # Work on a fresh dict so the caller's data is untouched.
    result: Dict[str, List[str]] = {k: list(v) for k, v in capabilities.items()}

    # Step 2.1
    _handle_test_module(result, command_params, param_defaults)

    # Step 2.1.5 - manual override (source of truth for listed commands)
    handled_commands = _apply_manual_mapping(
        result, command_params, manual_command_to_capability
    )

    if len(result) == 2:
        # Step 2.2 - single-capability shortcut (skip 2.3)
        _single_capability_shortcut(result, command_params, handled_commands)
    else:
        # Step 2.3 - multi-capability mapping
        _multi_capability_mapping(result, command_params, handled_commands)

    # Step 2.4 - deduplicate
    _deduplicate(result)

    # Step 2.5 - orphan logging
    _log_orphans(result, param_defaults)

    return result


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
@main.command()
def generate_param_mapping(
    command_params_json: str = typer.Argument(
        ..., help="JSON string with the {integration, commands} structure."
    ),
    param_defaults_json: str = typer.Argument(
        ..., help="JSON string mapping param names to their default values."
    ),
    integration_yml_path: Path = typer.Argument(
        ..., exists=True, help="Path to the integration YML file."
    ),
    manual_command_to_capability_json: str = typer.Argument(
        "{}",
        help=(
            "JSON string mapping command name -> list of capability names. "
            "Acts as source of truth, overriding automatic routing. "
            "Pass '{}' or omit to disable."
        ),
    ),
    output_path: Path = typer.Option(
        Path("./param_mapping_output.json"),
        "-o",
        "--output",
        help="Output JSON file path.",
    ),
) -> None:
    """Generate the connector parameter mapping from the integration YML and
    the supplied command/defaults JSON inputs (with optional manual overrides)."""
    logging_setup(calling_function=__name__)

    command_params: Dict[str, Any] = json.loads(command_params_json)
    param_defaults: Dict[str, Any] = json.loads(param_defaults_json)
    manual_command_to_capability: Dict[str, List[str]] = json.loads(
        manual_command_to_capability_json
    )
    with open(integration_yml_path) as f:
        integration_yml: dict = yaml.safe_load(f)

    capabilities = decide_capabilities(integration_yml)
    result = map_params_to_capabilities(
        capabilities, command_params, param_defaults, manual_command_to_capability
    )

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"Param mapping written to {output_path}")


if __name__ == "__main__":
    main()
