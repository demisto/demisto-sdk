"""AgentixActionSplitter — splits a script action into a Script YAML and an AgentixAction YAML."""

import copy
from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml.scalarstring import (  # noqa: TID251 - only importing FoldedScalarString is OK
    FoldedScalarString,
)

from demisto_sdk.commands.common.constants import DEFAULT_CONTENT_ITEM_TO_VERSION
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.parsers.base_content import validate_structure
from demisto_sdk.commands.content_graph.strict_objects.agentix_action import (
    AgentixAction as StrictAgentixAction,
)
from demisto_sdk.commands.content_graph.strict_objects.script import StrictScript

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction


class AgentixActionSplitter:
    """Splits a script action into (script_dict, action_dict).

    A script action is an AgentixAction YAML that contains a `script:` sub-key (a dict)
    with at least `dockerimage`. The splitter:
    1. Generates a Script YAML dict from the action's fields + script_config overrides.
    2. Generates a cleaned AgentixAction YAML dict (strips `script:` sub-key, fills
       `underlyingcontentitem`, auto-fills `underlyingargname`/`underlyingoutputcontextpath`).
    """

    @staticmethod
    def split(
        path: Path,
        action: "AgentixAction",
        py_code: str,
        processed_data: dict,
    ) -> tuple[dict, dict]:
        """Split a script action into (script_dict, action_dict). Validates both.

        Args:
            path: Path to the action YAML file (for error messages).
            action: The AgentixAction object (for pre-filled attributes).
            py_code: The Python script code.
            processed_data: Marketplace-processed action data (from super().prepare_for_upload()).

        Returns:
            (script_dict, action_dict) — both validated against their strict schemas.

        Raises:
            pydantic.ValidationError: If the generated script dict is invalid.
            ValueError: If the generated action dict is invalid.
        """
        script_dict = AgentixActionSplitter.generate_script_dict(action, py_code)
        action_dict = AgentixActionSplitter.generate_action_dict(action, processed_data)
        # Validate action dict (script dict already validated via StrictScript construction)
        action_errors = validate_structure(StrictAgentixAction, action_dict, path)
        if action_errors:
            raise ValueError(
                f"AgentixActionSplitter generated invalid action for {path}:\n"
                + "\n".join(str(e) for e in action_errors)
            )
        return script_dict, action_dict

    @staticmethod
    def generate_script_dict(action: "AgentixAction", py_code: str) -> dict:
        """Build the script dict using StrictScript for field correctness and serialization.

        Explicit field mapping (no generic merge):
        1. Build action-derived base fields (id, name, code, args, outputs, fromversion, etc.)
        2. Apply explicit script_config fields: dockerimage, standalone→internal, runonce, runas
        3. Construct StrictScript(**merged) for validation + serialization
        """
        script_cfg = action.script_config

        # standalone=None or False → script is internal (hidden); standalone=True → not internal
        if script_cfg is not None and script_cfg.standalone is not None:
            script_internal = not script_cfg.standalone
        else:
            script_internal = True  # default: generated scripts are internal

        # action.internal=True also forces script internal (top-level action field)
        script_internal = script_internal or action.internal

        base = {
            "commonfields": {"id": action.object_id, "version": -1},
            "name": action.object_id,
            "script": py_code,
            "type": "python",
            "subtype": "python3",
            "comment": action.description or "",
            "enabled": True,
            "scripttarget": 0,
            "args": AgentixActionSplitter._map_args(action.data.get("args", []))
            or None,
            "outputs": AgentixActionSplitter._map_outputs(
                action.data.get("outputs", [])
            )
            or None,
            "fromversion": action.fromversion,
            "toversion": (
                action.toversion
                if action.toversion != DEFAULT_CONTENT_ITEM_TO_VERSION
                else None
            ),
            "marketplaces": [mp.value for mp in action.marketplaces] or None,
            "supportedModules": action.supportedModules or None,
            "dockerimage": script_cfg.dockerimage if script_cfg else None,
            "internal": script_internal or None,
            "runonce": script_cfg.runonce if script_cfg else None,
            "runas": script_cfg.run_as if script_cfg else None,
            "dependson": script_cfg.depends_on if script_cfg else None,
        }

        # Filter None values, then construct StrictScript for validation + serialization
        script_input = {k: v for k, v in base.items() if v is not None}
        script_obj = StrictScript(**script_input)  # type: ignore[operator]
        # json() serializes enums to their string values; parse back to plain Python types
        raw = JSON_Handler().loads(script_obj.json(by_alias=True, exclude_none=True))
        # Exclude empty dicts (e.g. dependson defaults to {})
        result = {k: v for k, v in raw.items() if v != {}}
        # Render the script code as a YAML block scalar (script: |\n  ...) instead of a quoted string
        if "script" in result and isinstance(result["script"], str):
            result["script"] = FoldedScalarString(result["script"])
        return result

    @staticmethod
    def generate_action_dict(action: "AgentixAction", processed_data: dict) -> dict:
        """Build the cleaned action dict from marketplace-processed data + parser-filled attributes.

        Args:
            action: The AgentixAction object (for pre-filled underlying_content_item_* attributes).
            processed_data: Marketplace-processed action data.
        """
        action_dict = copy.deepcopy(processed_data)
        # Strip the entire script: sub-key (SDK-only authoring section)
        action_dict.pop("script", None)
        # Build underlyingcontentitem from parser-filled attributes
        action_dict["underlyingcontentitem"] = {
            "id": action.underlying_content_item_id,
            "name": action.underlying_content_item_name,
            "type": action.underlying_content_item_type,
            "version": action.underlying_content_item_version,
            "command": action.underlying_content_item_command or "",
        }
        # Auto-fill underlyingargname on each arg (if missing)
        for arg in action_dict.get("args", []):
            arg.setdefault("underlyingargname", arg["name"])
        # Auto-fill underlyingoutputcontextpath on each output (if missing)
        for output in action_dict.get("outputs", []):
            output.setdefault("underlyingoutputcontextpath", output["name"])
        return action_dict

    @staticmethod
    def _map_args(args: list) -> list:
        """Map action args to script args — drop action-specific fields."""
        SCRIPT_ARG_FIELDS = {
            "name",
            "description",
            "required",
            "defaultvalue",
            "hidden",
        }
        return [
            {k: v for k, v in arg.items() if k in SCRIPT_ARG_FIELDS} for arg in args
        ]

    @staticmethod
    def _map_outputs(outputs: list) -> list:
        """Map action outputs to script outputs — rename underlyingoutputcontextpath → contextPath."""
        result = []
        for output in outputs:
            script_output = {
                "contextPath": output.get("underlyingoutputcontextpath")
                or output.get("name"),
                "description": output.get("description", ""),
                "type": output.get("type"),
            }
            result.append({k: v for k, v in script_output.items() if v is not None})
        return result
