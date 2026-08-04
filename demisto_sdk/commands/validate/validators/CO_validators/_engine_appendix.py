"""Shared constants and helpers for CO125/CO126/CO127/CO128 engine
validators.

Appendix G (§2.6.2) — integrations that must NEVER emit engine or proxy
fields. Enforced by CO127; honored as skip-guard by CO125/CO126.

Appendix H (§2.6.2) — integrations that emit ``engine_mode`` with only 2
options (no engine / engine) and MUST NOT emit ``engine_group``. Enforced
by CO128; adjusts CO125 expectations for these integrations.

The lists carry integration ids (as they appear in ``handler.
related_integration.object_id``) in a normalized (lower-cased, dash-and-
underscore-agnostic) form. Use :func:`normalize_integration_id` when
comparing.
"""

from __future__ import annotations

from typing import Iterable, Set

from demisto_sdk.commands.content_graph.objects.connector import Connector

# ============================================================
# Appendix G - engine/proxy exclusion list (CO127)
# ============================================================
#
# Names copied verbatim from the manifest. Normalized to lower-case with
# spaces/dashes/underscores stripped for a robust lookup.
_APPENDIX_G_RAW = [
    "EDL",
    "ExportIndicators",
    "PingCastle",
    "Publish List",
    "Simple API Proxy",
    "Syslog v2",
    "TAXII Server",
    "TAXII2 Server",
    "Web File Repository",
    "Workday_IAM_Event_Generator",
    "XSOAR-Web-Server",
    "Microsoft Teams",
    "AWS-SNS-Listener",
]

# ============================================================
# Appendix H - single-engine list (CO128)
# ============================================================
_APPENDIX_H_RAW = [
    "saml",
    "slack",
    "sharedagent",
    "syslog",
    "mattermost",
    "duo",
]


def normalize_integration_id(name: str) -> str:
    """Normalize an integration id for Appendix comparison.

    Lowercases and strips ``-``/``_``/whitespace so that
    ``TAXII2 Server`` == ``taxii2server`` == ``taxii2_server``.
    """
    return (
        name.lower()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )


APPENDIX_G_EXCLUSION: Set[str] = {
    normalize_integration_id(n) for n in _APPENDIX_G_RAW
}
APPENDIX_H_SINGLE_ENGINE: Set[str] = {
    normalize_integration_id(n) for n in _APPENDIX_H_RAW
}

# ============================================================
# Engine field ids
# ============================================================
#
# The "engine triplet" that CO125/CO126 look for. ``engine_mode`` is the
# UI picker; ``engine`` and ``engine_group`` are dynamic dropdowns. Some
# YAMLs use camelCase ``engineGroup`` - we accept either spelling.
ENGINE_MODE_ID = "engine_mode"
ENGINE_ID = "engine"
ENGINE_GROUP_IDS = {"engine_group", "engineGroup"}


def is_appendix_g_integration(integration_id: str) -> bool:
    """Return True iff ``integration_id`` matches an entry on Appendix G
    (engine/proxy exclusion list)."""
    return normalize_integration_id(integration_id) in APPENDIX_G_EXCLUSION


def is_appendix_h_integration(integration_id: str) -> bool:
    """Return True iff ``integration_id`` matches an entry on Appendix H
    (single-engine list)."""
    return normalize_integration_id(integration_id) in APPENDIX_H_SINGLE_ENGINE


def connector_xsoar_integration_ids(connector: Connector) -> Iterable[str]:
    """Yield the object_id of every resolved integration referenced by an
    XSOAR handler on the connector. Used by CO125-CO128 to determine
    whether Appendix G/H applies.
    """
    for h in connector.handlers:
        if not h.is_xsoar:
            continue
        integration = h.related_integration
        if integration is None:
            continue
        obj_id = getattr(integration, "object_id", None)
        if obj_id:
            yield obj_id


def connector_is_appendix_g(connector: Connector) -> bool:
    """Return True iff ANY XSOAR handler on the connector resolves to an
    Appendix G integration. Used by CO125/CO126 to short-circuit
    validation for exclusion-list integrations.
    """
    return any(
        is_appendix_g_integration(obj_id)
        for obj_id in connector_xsoar_integration_ids(connector)
    )


def connector_is_appendix_h(connector: Connector) -> bool:
    """Return True iff ANY XSOAR handler on the connector resolves to an
    Appendix H (single-engine) integration."""
    return any(
        is_appendix_h_integration(obj_id)
        for obj_id in connector_xsoar_integration_ids(connector)
    )
