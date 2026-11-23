"""Support for the local command configuration file (``.demisto-sdk-conf``).

The file sets default values for command options, one section per command::

    [pre-commit]
    docker=false
    mode=nightly

The values are fed into Click's ``default_map``, which is consulted only when an
option was given neither on the command line nor through an environment
variable. That yields the expected precedence:

    command line > environment variable > configuration file > option default

Resolving the file through Click (rather than overwriting the already-bound
arguments of individual commands) means every command supports the
configuration file, and each value is cast by its own parameter type.
"""

from configparser import ConfigParser
from configparser import Error as ConfigParserError
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

import click

from demisto_sdk.commands.common.constants import DEMISTO_SDK_CONFIG_FILE
from demisto_sdk.commands.common.logger import logger

# Sections whose name never matched the name of the command they configure.
# Kept so that configuration files written before the file was applied through
# Click keep working.
SECTION_ALIASES: Dict[str, str] = {
    "error-code-info": "error-code",
    "unify": "prepare-content",
}


def _params_by_name(command: click.Command) -> Dict[str, click.Parameter]:
    """Index a command's parameters by their name and by their long flag names.

    The README tells users to write the flag's full name with underscores
    instead of dashes (``no_docker_checks``), which is not always the parameter
    name Click uses internally (``--input`` may be bound to ``input_files``), so
    both spellings are accepted.
    """
    params: Dict[str, click.Parameter] = {}
    for param in command.params:
        if not param.name:
            continue
        params[param.name] = param
        for opt in (*param.opts, *param.secondary_opts):
            if opt.startswith("--"):
                params[opt[2:].replace("-", "_")] = param
    return params


def _section_defaults(
    command: Optional[click.Command], section: Mapping[str, Any]
) -> Dict[str, Any]:
    """Convert the raw strings of a single section into Click defaults.

    Click casts ``default_map`` values with the parameter's own type, so strings
    are handed over untouched - except for multi-value parameters, where a bare
    string would be consumed character by character instead of as one value.
    """
    if command is None:
        # The command was not registered for this run, so Click will never look
        # its section up. Pass the values through rather than guessing types.
        return dict(section)

    params = _params_by_name(command)
    defaults: Dict[str, Any] = {}
    for key, raw_value in section.items():
        param = params.get(key)
        if param is None:
            logger.debug(
                f"Ignoring unknown option '{key}' of command '{command.name}' in {DEMISTO_SDK_CONFIG_FILE}"
            )
            defaults[key] = raw_value
            continue
        value: Any = raw_value
        if isinstance(raw_value, str) and (param.multiple or param.nargs == -1):
            value = [item.strip() for item in raw_value.split(",") if item.strip()]
        defaults[str(param.name)] = value
    return defaults


def apply_config_file_defaults(
    ctx: click.Context,
    config_file_path: Union[str, Path] = DEMISTO_SDK_CONFIG_FILE,
) -> None:
    """Load the configuration file into the ``default_map`` of the root context.

    Click passes ``default_map[<command name>]`` down to each subcommand
    context, so this has to run in the root callback, before the subcommand
    context is created. A missing or unreadable file is not an error - the
    commands simply run with their own defaults.
    """
    path = Path(config_file_path)
    if not path.is_file():
        return

    config = ConfigParser(allow_no_value=True)
    try:
        config.read(path)
    except (ConfigParserError, OSError, UnicodeDecodeError) as error:
        logger.warning(f"<yellow>Could not read {path}: {error}</yellow>")
        return

    if not config.sections():
        return

    group = ctx.command if isinstance(ctx.command, click.Group) else None
    default_map = dict(ctx.default_map or {})
    for section in config.sections():
        values = dict(config[section])
        # A section may configure more than one command name (see SECTION_ALIASES).
        for command_name in dict.fromkeys(
            (section, SECTION_ALIASES.get(section, section))
        ):
            command = group.get_command(ctx, command_name) if group else None
            defaults = dict(default_map.get(command_name) or {})
            defaults.update(_section_defaults(command, values))
            default_map[command_name] = defaults

    ctx.default_map = default_map
    logger.debug(f"Applied defaults from {path}: {default_map}")
