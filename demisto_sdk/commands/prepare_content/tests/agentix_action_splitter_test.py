"""Unit tests for AgentixActionSplitter."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.strict_objects.agentix_action import (
    ScriptConfig,
)


def _make_action(
    object_id: str = "CortexIsolateEndpoint",
    description: str = "Isolates an endpoint.",
    fromversion: str = "8.12.0",
    toversion: str = "99.99.99",
    marketplaces=None,
    supported_modules=None,
    internal: bool = False,
    script_config: ScriptConfig = None,
    args: list = None,
    outputs: list = None,
    underlying_content_item_id: str = None,
    underlying_content_item_name: str = None,
    underlying_content_item_type: str = "script",
    underlying_content_item_command: str = "",
    underlying_content_item_version: int = -1,
):
    """Build a minimal mock AgentixAction for splitter tests."""
    action = MagicMock()
    action.object_id = object_id
    action.description = description
    action.fromversion = fromversion
    action.toversion = toversion
    action.marketplaces = (
        [MarketplaceVersions.PLATFORM] if marketplaces is None else marketplaces
    )
    action.supportedModules = supported_modules or ["xsiam"]
    action.internal = internal
    action.script_config = script_config or ScriptConfig(
        dockerimage="demisto/python3:3.12.12.6391686"
    )
    action.data = {
        "args": args or [],
        "outputs": outputs or [],
    }
    action.underlying_content_item_id = underlying_content_item_id or object_id
    action.underlying_content_item_name = underlying_content_item_name or object_id
    action.underlying_content_item_type = underlying_content_item_type
    action.underlying_content_item_command = underlying_content_item_command
    action.underlying_content_item_version = underlying_content_item_version
    return action


PY_CODE = "def main():\n    pass\n"
ACTION_PATH = Path(
    "/fake/AgentixActions/CortexIsolateEndpoint/CortexIsolateEndpoint.yaml"
)


def test_split_basic():
    """
    Given:
        - A minimal script action with dockerimage.
    When:
        - Calling AgentixActionSplitter.split().
    Then:
        - Returns (script_dict, action_dict) both valid.
        - script_dict has type=python, subtype=python3, dockerimage.
        - action_dict has underlyingcontentitem.
    """
    from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
        AgentixActionSplitter,
    )

    action = _make_action()
    processed_data = {
        "commonfields": {"id": "CortexIsolateEndpoint", "version": -1},
        "name": "CortexIsolateEndpoint",
        "display": "Cortex - Isolate Endpoint",
        "description": "Isolates an endpoint.",
        "script": {"dockerimage": "demisto/python3:3.12.12.6391686"},
        "fromversion": "8.12.0",
        "marketplaces": ["platform"],
    }
    script_dict, action_dict = AgentixActionSplitter.split(
        ACTION_PATH, action, PY_CODE, processed_data
    )
    assert script_dict["type"] == "python"
    assert script_dict["subtype"] == "python3"
    assert script_dict["dockerimage"] == "demisto/python3:3.12.12.6391686"
    assert "underlyingcontentitem" in action_dict
    assert "script" not in action_dict  # script: sub-key stripped


def test_split_internal_action_true():
    """
    Given:
        - A script action with action.internal=True.
    When:
        - Calling AgentixActionSplitter.split().
    Then:
        - script_dict["internal"] is True.
        - action_dict["internal"] is True.
    """
    from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
        AgentixActionSplitter,
    )

    action = _make_action(internal=True)
    processed_data = {
        "commonfields": {"id": "CortexIsolateEndpoint", "version": -1},
        "name": "CortexIsolateEndpoint",
        "display": "Cortex - Isolate Endpoint",
        "description": "Isolates an endpoint.",
        "internal": True,
        "script": {"dockerimage": "demisto/python3:3.12.12.6391686"},
        "fromversion": "8.12.0",
        "marketplaces": ["platform"],
    }
    script_dict, action_dict = AgentixActionSplitter.split(
        ACTION_PATH, action, PY_CODE, processed_data
    )
    assert script_dict.get("internal") is True
    assert action_dict.get("internal") is True


def test_split_standalone_false_makes_script_internal():
    """
    Given:
        - A script action with standalone=False (explicit) and action.internal=False.
    When:
        - Calling AgentixActionSplitter.split().
    Then:
        - script_dict["internal"] is True (standalone=False → internal=True).
        - action_dict has no "internal" key (or it's False/absent).
    """
    from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
        AgentixActionSplitter,
    )

    script_cfg = ScriptConfig(
        dockerimage="demisto/python3:3.12.12.6391686", standalone=False
    )
    action = _make_action(internal=False, script_config=script_cfg)
    processed_data = {
        "commonfields": {"id": "CortexIsolateEndpoint", "version": -1},
        "name": "CortexIsolateEndpoint",
        "display": "Cortex - Isolate Endpoint",
        "description": "Isolates an endpoint.",
        "script": {
            "dockerimage": "demisto/python3:3.12.12.6391686",
            "standalone": False,
        },
        "fromversion": "8.12.0",
        "marketplaces": ["platform"],
    }
    script_dict, action_dict = AgentixActionSplitter.split(
        ACTION_PATH, action, PY_CODE, processed_data
    )
    assert script_dict.get("internal") is True
    assert not action_dict.get("internal")


def test_split_standalone_true_makes_script_not_internal():
    """
    Given:
        - A script action with standalone=True and action.internal=False.
    When:
        - Calling AgentixActionSplitter.split().
    Then:
        - script_dict["internal"] is absent/False (standalone=True → internal=False).
        - action_dict has no "internal" key.
    """
    from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
        AgentixActionSplitter,
    )

    script_cfg = ScriptConfig(
        dockerimage="demisto/python3:3.12.12.6391686", standalone=True
    )
    action = _make_action(internal=False, script_config=script_cfg)
    processed_data = {
        "commonfields": {"id": "CortexIsolateEndpoint", "version": -1},
        "name": "CortexIsolateEndpoint",
        "display": "Cortex - Isolate Endpoint",
        "description": "Isolates an endpoint.",
        "script": {
            "dockerimage": "demisto/python3:3.12.12.6391686",
            "standalone": True,
        },
        "fromversion": "8.12.0",
        "marketplaces": ["platform"],
    }
    script_dict, action_dict = AgentixActionSplitter.split(
        ACTION_PATH, action, PY_CODE, processed_data
    )
    assert not script_dict.get("internal")
    assert not action_dict.get("internal")


def test_split_standalone_none_default_internal():
    """
    Given:
        - A script action with standalone not set (None) and action.internal=False.
    When:
        - Calling AgentixActionSplitter.split().
    Then:
        - script_dict["internal"] is True (default: generated scripts are internal).
        - action_dict has no "internal" key.
    """
    from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
        AgentixActionSplitter,
    )

    action = _make_action(internal=False)
    processed_data = {
        "commonfields": {"id": "CortexIsolateEndpoint", "version": -1},
        "name": "CortexIsolateEndpoint",
        "display": "Cortex - Isolate Endpoint",
        "description": "Isolates an endpoint.",
        "script": {"dockerimage": "demisto/python3:3.12.12.6391686"},
        "fromversion": "8.12.0",
        "marketplaces": ["platform"],
    }
    script_dict, action_dict = AgentixActionSplitter.split(
        ACTION_PATH, action, PY_CODE, processed_data
    )
    assert script_dict.get("internal") is True
    assert not action_dict.get("internal")


def test_split_strips_script_key():
    """
    Given:
        - processed_data with a script: sub-key.
    When:
        - Calling AgentixActionSplitter.split().
    Then:
        - action_dict does NOT contain the "script" key.
    """
    from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
        AgentixActionSplitter,
    )

    action = _make_action()
    processed_data = {
        "commonfields": {"id": "CortexIsolateEndpoint", "version": -1},
        "name": "CortexIsolateEndpoint",
        "display": "Cortex - Isolate Endpoint",
        "description": "Isolates an endpoint.",
        "script": {"dockerimage": "demisto/python3:3.12.12.6391686"},
        "fromversion": "8.12.0",
        "marketplaces": ["platform"],
    }
    _, action_dict = AgentixActionSplitter.split(
        ACTION_PATH, action, PY_CODE, processed_data
    )
    assert "script" not in action_dict


def test_split_fills_underlyingcontentitem():
    """
    Given:
        - A script action with underlying_content_item_* attributes set.
    When:
        - Calling AgentixActionSplitter.split().
    Then:
        - action_dict["underlyingcontentitem"] is auto-filled from the action's attributes.
    """
    from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
        AgentixActionSplitter,
    )

    action = _make_action(
        object_id="MyAction",
        underlying_content_item_id="MyAction",
        underlying_content_item_name="MyAction",
        underlying_content_item_type="script",
        underlying_content_item_version=-1,
    )
    processed_data = {
        "commonfields": {"id": "MyAction", "version": -1},
        "name": "MyAction",
        "display": "My Action",
        "description": "Test.",
        "script": {"dockerimage": "demisto/python3:3.12.12.6391686"},
        "fromversion": "8.12.0",
        "marketplaces": ["platform"],
    }
    _, action_dict = AgentixActionSplitter.split(
        ACTION_PATH, action, PY_CODE, processed_data
    )
    uci = action_dict["underlyingcontentitem"]
    assert uci["id"] == "MyAction"
    assert uci["name"] == "MyAction"
    assert uci["type"] == "script"
    assert uci["version"] == -1


def test_split_fills_underlyingargname():
    """
    Given:
        - A script action with args that have no underlyingargname.
    When:
        - Calling AgentixActionSplitter.split().
    Then:
        - Each arg in action_dict["args"] has underlyingargname set (auto-filled from name).
    """
    from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
        AgentixActionSplitter,
    )

    action = _make_action()
    processed_data = {
        "commonfields": {"id": "CortexIsolateEndpoint", "version": -1},
        "name": "CortexIsolateEndpoint",
        "display": "Cortex - Isolate Endpoint",
        "description": "Isolates an endpoint.",
        "script": {"dockerimage": "demisto/python3:3.12.12.6391686"},
        "args": [
            {"name": "endpoint_id", "description": "The endpoint ID.", "type": "string"}
        ],
        "fromversion": "8.12.0",
        "marketplaces": ["platform"],
    }
    _, action_dict = AgentixActionSplitter.split(
        ACTION_PATH, action, PY_CODE, processed_data
    )
    assert action_dict["args"][0]["underlyingargname"] == "endpoint_id"


def test_split_fills_underlyingoutputcontextpath():
    """
    Given:
        - A script action with outputs that have no underlyingoutputcontextpath.
    When:
        - Calling AgentixActionSplitter.split().
    Then:
        - Each output in action_dict["outputs"] has underlyingoutputcontextpath set.
    """
    from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
        AgentixActionSplitter,
    )

    action = _make_action()
    processed_data = {
        "commonfields": {"id": "CortexIsolateEndpoint", "version": -1},
        "name": "CortexIsolateEndpoint",
        "display": "Cortex - Isolate Endpoint",
        "description": "Isolates an endpoint.",
        "script": {"dockerimage": "demisto/python3:3.12.12.6391686"},
        "outputs": [
            {
                "name": "Core.Isolation.endpoint_id",
                "description": "The endpoint ID.",
                "type": "String",
            }
        ],
        "fromversion": "8.12.0",
        "marketplaces": ["platform"],
    }
    _, action_dict = AgentixActionSplitter.split(
        ACTION_PATH, action, PY_CODE, processed_data
    )
    assert (
        action_dict["outputs"][0]["underlyingoutputcontextpath"]
        == "Core.Isolation.endpoint_id"
    )


def test_split_args_mapping():
    """
    Given:
        - A script action with args containing action-specific fields.
    When:
        - Calling AgentixActionSplitter.split().
    Then:
        - script_dict["args"] contains only SCRIPT_ARG_FIELDS.
        - type, underlyingargname, disabled, isgeneratable are absent.
    """
    from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
        AgentixActionSplitter,
    )

    raw_args = [
        {
            "name": "endpoint_id",
            "description": "The endpoint ID.",
            "required": True,
            "type": "string",
            "underlyingargname": "endpoint_id",
            "disabled": False,
            "isgeneratable": False,
        }
    ]
    action = _make_action(args=raw_args)
    processed_data = {
        "commonfields": {"id": "CortexIsolateEndpoint", "version": -1},
        "name": "CortexIsolateEndpoint",
        "display": "Cortex - Isolate Endpoint",
        "description": "Isolates an endpoint.",
        "script": {"dockerimage": "demisto/python3:3.12.12.6391686"},
        "args": raw_args,
        "fromversion": "8.12.0",
        "marketplaces": ["platform"],
    }
    script_dict, _ = AgentixActionSplitter.split(
        ACTION_PATH, action, PY_CODE, processed_data
    )
    script_arg = script_dict["args"][0]
    assert "name" in script_arg
    assert "description" in script_arg
    assert "required" in script_arg
    assert "type" not in script_arg
    assert "underlyingargname" not in script_arg
    assert "disabled" not in script_arg
    assert "isgeneratable" not in script_arg


def test_split_outputs_mapping():
    """
    Given:
        - A script action with outputs containing action-specific fields.
    When:
        - Calling AgentixActionSplitter.split().
    Then:
        - script_dict["outputs"] uses contextPath (not name).
        - underlyingoutputcontextpath and disabled are absent.
    """
    from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
        AgentixActionSplitter,
    )

    raw_outputs = [
        {
            "name": "Core.Isolation.endpoint_id",
            "description": "The endpoint ID.",
            "type": "String",
            "underlyingoutputcontextpath": "Core.Isolation.endpoint_id",
            "disabled": False,
        }
    ]
    action = _make_action(outputs=raw_outputs)
    processed_data = {
        "commonfields": {"id": "CortexIsolateEndpoint", "version": -1},
        "name": "CortexIsolateEndpoint",
        "display": "Cortex - Isolate Endpoint",
        "description": "Isolates an endpoint.",
        "script": {"dockerimage": "demisto/python3:3.12.12.6391686"},
        "outputs": raw_outputs,
        "fromversion": "8.12.0",
        "marketplaces": ["platform"],
    }
    script_dict, _ = AgentixActionSplitter.split(
        ACTION_PATH, action, PY_CODE, processed_data
    )
    script_output = script_dict["outputs"][0]
    assert "contextPath" in script_output
    assert script_output["contextPath"] == "Core.Isolation.endpoint_id"
    assert "name" not in script_output
    assert "underlyingoutputcontextpath" not in script_output
    assert "disabled" not in script_output


def test_split_runonce():
    """
    Given:
        - A script action with runonce=True in script_config.
    When:
        - Calling AgentixActionSplitter.split().
    Then:
        - script_dict["runonce"] is True.
    """
    from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
        AgentixActionSplitter,
    )

    script_cfg = ScriptConfig(
        dockerimage="demisto/python3:3.12.12.6391686", runonce=True
    )
    action = _make_action(script_config=script_cfg)
    processed_data = {
        "commonfields": {"id": "CortexIsolateEndpoint", "version": -1},
        "name": "CortexIsolateEndpoint",
        "display": "Cortex - Isolate Endpoint",
        "description": "Isolates an endpoint.",
        "script": {"dockerimage": "demisto/python3:3.12.12.6391686", "runonce": True},
        "fromversion": "8.12.0",
        "marketplaces": ["platform"],
    }
    script_dict, _ = AgentixActionSplitter.split(
        ACTION_PATH, action, PY_CODE, processed_data
    )
    assert script_dict.get("runonce") is True


def test_split_runas():
    """
    Given:
        - A script action with runas="DBotRole" in script_config.
    When:
        - Calling AgentixActionSplitter.split().
    Then:
        - script_dict["runas"] is "DBotRole".
    """
    from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
        AgentixActionSplitter,
    )

    script_cfg = ScriptConfig(
        dockerimage="demisto/python3:3.12.12.6391686", runas="DBotRole"
    )
    action = _make_action(script_config=script_cfg)
    processed_data = {
        "commonfields": {"id": "CortexIsolateEndpoint", "version": -1},
        "name": "CortexIsolateEndpoint",
        "display": "Cortex - Isolate Endpoint",
        "description": "Isolates an endpoint.",
        "script": {
            "dockerimage": "demisto/python3:3.12.12.6391686",
            "runas": "DBotRole",
        },
        "fromversion": "8.12.0",
        "marketplaces": ["platform"],
    }
    script_dict, _ = AgentixActionSplitter.split(
        ACTION_PATH, action, PY_CODE, processed_data
    )
    assert script_dict.get("runas") == "DBotRole"


def test_split_dependson():
    """
    Given:
        - A script action with dependson in script_config.
    When:
        - Calling AgentixActionSplitter.split().
    Then:
        - script_dict contains the dependson field.
    """
    from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
        AgentixActionSplitter,
    )

    script_cfg = ScriptConfig(
        dockerimage="demisto/python3:3.12.12.6391686",
        dependson={"must": ["some-command"]},
    )
    action = _make_action(script_config=script_cfg)
    processed_data = {
        "commonfields": {"id": "CortexIsolateEndpoint", "version": -1},
        "name": "CortexIsolateEndpoint",
        "display": "Cortex - Isolate Endpoint",
        "description": "Isolates an endpoint.",
        "script": {
            "dockerimage": "demisto/python3:3.12.12.6391686",
            "dependson": {"must": ["some-command"]},
        },
        "fromversion": "8.12.0",
        "marketplaces": ["platform"],
    }
    script_dict, _ = AgentixActionSplitter.split(
        ACTION_PATH, action, PY_CODE, processed_data
    )
    assert script_dict.get("dependson") == {"must": ["some-command"]}


def test_split_unknown_field_rejected():
    """
    Given:
        - A ScriptConfig with a truly unknown field (not in the allowed list).
    When:
        - Constructing ScriptConfig.
    Then:
        - pydantic.ValidationError is raised (extra fields are forbidden).
    """
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        ScriptConfig(
            dockerimage="demisto/python3:3.12.12.6391686",
            unknownfield="not-allowed",  # truly unknown field
        )


def test_split_fromversion_toversion_inherited():
    """
    Given:
        - A script action with fromversion=8.12.0.
    When:
        - Calling AgentixActionSplitter.split().
    Then:
        - script_dict["fromversion"] equals action.fromversion.
    """
    from demisto_sdk.commands.prepare_content.agentix_action_splitter import (
        AgentixActionSplitter,
    )

    action = _make_action(fromversion="8.12.0")
    processed_data = {
        "commonfields": {"id": "CortexIsolateEndpoint", "version": -1},
        "name": "CortexIsolateEndpoint",
        "display": "Cortex - Isolate Endpoint",
        "description": "Isolates an endpoint.",
        "script": {"dockerimage": "demisto/python3:3.12.12.6391686"},
        "fromversion": "8.12.0",
        "marketplaces": ["platform"],
    }
    script_dict, _ = AgentixActionSplitter.split(
        ACTION_PATH, action, PY_CODE, processed_data
    )
    assert script_dict["fromversion"] == "8.12.0"


def test_split_validation_error():
    """
    Given:
        - A ScriptConfig with an invalid type for runonce (string instead of bool).
    When:
        - Constructing ScriptConfig.
    Then:
        - pydantic.ValidationError is raised (type mismatch).
    """
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        ScriptConfig(
            dockerimage="demisto/python3:3.12.12.6391686",
            runonce="not-a-bool",  # invalid type for runonce field
        )
