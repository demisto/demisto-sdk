"""Scaffold or update a unified-connectors-content connector from an XSOAR integration.

This is the **template** version of the script. The two main entry points
(:func:`create_manifest_from_scratch` and :func:`add_handler_to_existing_connector`)
are intentionally left as empty stubs — per-file generation rules will be
added incrementally in subsequent iterations.

Usage:
    python -m demisto_sdk.scripts.manifest_generator \\
        Packs/Salesforce/Integrations/Salesforce/Salesforce.yml \\
        "Salesforce" \\
        '{"identity-posture-ai-security": ["sync_interval", "create_user_enabled"]}'
"""

import os

os.environ["DEMISTO_SDK_IGNORE_CONTENT_WARNING"] = "True"

from pathlib import Path
from typing import Any, Dict

import typer

from demisto_sdk.commands.common.handlers import (
    DEFAULT_JSON_HANDLER as json,
)
from demisto_sdk.commands.common.handlers import (
    DEFAULT_YAML_HANDLER as yaml,
)
from demisto_sdk.commands.common.logger import logger, logging_setup

main = typer.Typer()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def title_to_slug(title: str) -> str:
    """Derive a connector directory slug from its human title.

    Lowercases the title and removes all spaces. This is the canonical mapping
    from a connector's display title (e.g. ``"Microsoft Defender"``) to its
    directory name on disk (e.g. ``microsoftdefender``).
    """
    return title.strip().lower().replace(" ", "")


def connector_exists(connector_dir: Path) -> bool:
    """Return True if ``connector_dir`` looks like an already-initialized connector.

    A directory counts as an existing connector only when it both exists and
    contains a ``connector.yaml`` file at its root. This avoids treating empty
    or partially-created directories as existing connectors.
    """
    return connector_dir.is_dir() and (connector_dir / "connector.yaml").is_file()


def load_integration_yml(path: Path) -> dict:
    """Load and return the integration YAML at ``path`` as a dict."""
    if not path.is_file():
        raise FileNotFoundError(f"Integration yml not found: {path}")
    with open(path) as fh:
        return yaml.load(fh) or {}


def parse_mapped_params(raw: str) -> Dict[str, Any]:
    """Parse the ``mapped_params`` JSON string into a dict.

    The exact consumption of ``mapped_params`` is left to future iterations;
    for now this helper just guarantees we have a valid JSON object to pass
    down to the dispatch targets.
    """
    try:
        data = json.loads(raw)
    except Exception as exc:  # JSON handler may raise various errors
        raise ValueError(f"--mapped-params is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("--mapped-params must decode to a JSON object")
    return data


# ---------------------------------------------------------------------------
# Dispatch targets (stubs — per-file rules to be added later)
# ---------------------------------------------------------------------------
def create_manifest_from_scratch(
    connector_dir: Path,
    integration_yml: dict,
    connector_title: str,
    mapped_params: Dict[str, Any],
) -> None:
    """Create a brand-new connector folder from scratch.

    Will eventually produce::

        connector_dir/connector.yaml
        connector_dir/capabilities.yaml
        connector_dir/configurations.yaml
        connector_dir/connection.yaml
        connector_dir/components/handlers/<slug>/handler.yaml
        connector_dir/components/handlers/<slug>/serializer.yaml

    For now this is an intentionally empty stub — the file-by-file rules
    will be added in follow-up iterations.
    """
    logger.info(f"[manifest_generator] Creating new connector at {connector_dir}")
    # TODO: generate connector.yaml
    # TODO: generate capabilities.yaml
    # TODO: generate configurations.yaml
    # TODO: generate connection.yaml
    # TODO: generate components/handlers/<slug>/handler.yaml
    # TODO: generate components/handlers/<slug>/serializer.yaml


def add_handler_to_existing_connector(
    connector_dir: Path,
    integration_yml: dict,
    connector_title: str,
    mapped_params: Dict[str, Any],
) -> None:
    """Add a new handler under an existing connector and update shared files.

    Will eventually:

    * leave ``connector.yaml`` untouched
    * append new entries to ``capabilities.yaml`` / ``configurations.yaml``
      / ``connection.yaml`` (skipping ids that already exist)
    * create a fresh ``components/handlers/<slug>/`` directory containing
      ``handler.yaml`` and ``serializer.yaml``

    For now this is an intentionally empty stub — the file-by-file rules
    will be added in follow-up iterations.
    """
    logger.info(
        f"[manifest_generator] Adding handler to existing connector at {connector_dir}"
    )
    # TODO: append to capabilities.yaml (skip existing capability ids)
    # TODO: append to configurations.yaml
    # TODO: append to connection.yaml (skip existing profile ids)
    # TODO: create components/handlers/<slug>/handler.yaml
    # TODO: create components/handlers/<slug>/serializer.yaml


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
@main.command()
def generate_manifest(
    integration_path: Path = typer.Argument(
        ...,
        exists=True,
        help="Path to the XSOAR integration YML file.",
    ),
    connector_title: str = typer.Argument(
        ...,
        help="Human-readable connector title (e.g. 'Salesforce'). The "
        "directory slug is derived as title.lower().replace(' ', '').",
    ),
    mapped_params: str = typer.Argument(
        ...,
        help="JSON string output of connector_param_mapper.py "
        "(shape: {capability: [params]}).",
    ),
    connectors_root: Path = typer.Option(
        Path.cwd() / "connectors",
        "--connectors-root",
        help="Root directory under which connector folders live. "
        "Defaults to <CWD>/connectors.",
    ),
) -> None:
    """Scaffold a new connector or add a handler to an existing one.

    The script decides between the two paths automatically:

    * If ``<connectors_root>/<slug>/connector.yaml`` exists, only the
      handler is added (and shared files are updated).
    * Otherwise, the full connector folder is created from scratch.
    """
    logging_setup(calling_function=__name__)

    integration_yml = load_integration_yml(integration_path)
    mapped_params_dict = parse_mapped_params(mapped_params)

    slug = title_to_slug(connector_title)
    connector_dir = connectors_root / slug

    logger.info(
        f"[manifest_generator] integration={integration_path} "
        f"title={connector_title!r} slug={slug!r} target={connector_dir}"
    )

    if connector_exists(connector_dir):
        add_handler_to_existing_connector(
            connector_dir=connector_dir,
            integration_yml=integration_yml,
            connector_title=connector_title,
            mapped_params=mapped_params_dict,
        )
    else:
        create_manifest_from_scratch(
            connector_dir=connector_dir,
            integration_yml=integration_yml,
            connector_title=connector_title,
            mapped_params=mapped_params_dict,
        )


if __name__ == "__main__":
    main()
