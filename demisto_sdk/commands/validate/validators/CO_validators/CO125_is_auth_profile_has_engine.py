"""CO125 - every auth profile must expose the engine picker triplet.

This module also hosts the shared engine constants and Appendix G/H
integration lists that CO126, CO127, and CO128 import — the whole
CO125-CO128 band shares a single lookup surface here so we don't need a
separate helper file.

Public surface:
- Constants: ``ENGINE_MODE_ID``, ``ENGINE_ID``, ``ENGINE_GROUP_IDS``
- Appendix lookups: ``APPENDIX_G_EXCLUSION``, ``APPENDIX_H_SINGLE_ENGINE``,
  ``normalize_integration_id``, ``is_appendix_g_integration``,
  ``is_appendix_h_integration``, ``connector_is_appendix_g``,
  ``connector_is_appendix_h``, ``connector_xsoar_integration_ids``
- Serializer-aware field resolution:
  ``xsoar_handlers_for_profile``, ``profile_serialized_field_ids``,
  ``general_config_field_ids``
- Validator: ``IsAuthProfileHasEngineValidator`` (CO125 itself)
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Set

from demisto_sdk.commands.content_graph.objects.connector import (
    ConnectionProfile,
    Connector,
    FieldGroup,
    GeneralConfigurations,
    HandlerData,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

# ============================================================
# Engine field ids
# ============================================================
#
# The "engine triplet" that CO125/CO126 look for. ``engine_mode`` is the
# UI picker; ``engine`` and ``engine_group`` are dynamic dropdowns. Some
# on-disk YAMLs use camelCase ``engineGroup`` - we accept either
# spelling.
ENGINE_MODE_ID = "engine_mode"
ENGINE_ID = "engine"
ENGINE_GROUP_IDS: Set[str] = {"engine_group", "engineGroup"}

# ============================================================
# Appendix G - engine/proxy exclusion list (CO127)
# ============================================================
#
# Integrations that MUST NEVER emit engine/proxy fields. CO127 enforces
# the exclusion; CO125/CO126 honor it as a skip-guard.
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
#
# Integrations that emit ``engine_mode`` with only 2 options (no engine
# / engine) and MUST NOT emit ``engine_group``. CO128 enforces this;
# CO125 relaxes its expectations for these integrations.
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
    return name.lower().replace(" ", "").replace("-", "").replace("_", "")


APPENDIX_G_EXCLUSION: Set[str] = {normalize_integration_id(n) for n in _APPENDIX_G_RAW}
APPENDIX_H_SINGLE_ENGINE: Set[str] = {
    normalize_integration_id(n) for n in _APPENDIX_H_RAW
}


def is_appendix_g_integration(integration_id: str) -> bool:
    """Return True iff ``integration_id`` matches an entry on Appendix G
    (engine/proxy exclusion list)."""
    return normalize_integration_id(integration_id) in APPENDIX_G_EXCLUSION


def is_appendix_h_integration(integration_id: str) -> bool:
    """Return True iff ``integration_id`` matches an entry on Appendix H
    (single-engine list)."""
    return normalize_integration_id(integration_id) in APPENDIX_H_SINGLE_ENGINE


def connector_xsoar_integration_ids(connector: Connector) -> Iterable[str]:
    """Yield the object_id of every resolved integration referenced by
    an XSOAR handler on the connector. Used by CO125-CO128 to determine
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
    Appendix G integration. CO125/CO126 short-circuit on this.
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


# ============================================================
# Serializer-aware field id resolution
# ============================================================
#
# Grouped connectors namespace their connection.yaml field ids per
# profile (e.g. ``plain_qualys_fim_engine_mode``). Each XSOAR handler
# owns a ``serializer.yaml`` that rewrites those namespaced ids back to
# the canonical integration param name (e.g. ``engine_mode``). The
# parser already exposes those rewrites on
# ``handler.resolved_params[*]`` (same source CO120 uses).
#
# CO125/CO126/CO128 MUST look up engine fields by CANONICAL id after
# serializer rewrite, not by the raw connection.yaml id, otherwise every
# grouped connector with namespaced ids will false-positive.


def xsoar_handlers_for_profile(
    connector: Connector, profile_id: str
) -> Iterable[HandlerData]:
    """Yield every XSOAR handler that references ``profile_id`` via one
    of its ``capabilities[].auth_options[]``. Grouped connectors
    typically have exactly one XSOAR handler per profile, but tolerate
    more.
    """
    for h in connector.handlers:
        if not h.is_xsoar:
            continue
        for cap in h.capabilities:
            for opt in cap.auth_options or []:
                if opt.id == profile_id:
                    yield h
                    break
            else:
                continue
            break


def profile_serialized_field_ids(
    connector: Connector, profile: ConnectionProfile
) -> Set[str]:
    """Return the set of canonical (post-serializer) field ids exposed
    by ``profile``.

    A grouped connector's raw connection.yaml id
    ``plain_qualys_fim_engine_mode`` is resolved to its canonical name
    ``engine_mode`` via the owning XSOAR handler's ``resolved_params``
    (built from ``serializer.yaml`` at parse time). Raw ids that have no
    resolver entry map to themselves.
    """
    resolver: Dict[str, str] = {}
    for handler in xsoar_handlers_for_profile(connector, profile.id):
        for rp in handler.resolved_params:
            # If the same raw id resolves in multiple handlers, keep the
            # first mapping we see.
            if rp.connector_param_name in resolver:
                continue
            resolver[rp.connector_param_name] = rp.content_param_name

    canonical: Set[str] = set()
    for fg in profile.configurations:
        for field in fg.fields:
            if not field.id:
                continue
            canonical.add(resolver.get(field.id, field.id))
    return canonical


def general_config_field_ids(groups: Iterable[FieldGroup]) -> Set[str]:
    """Return the plain set of field ids inside a
    general_configurations-style list of ``FieldGroup``. Standard
    connectors don't run through per-profile serializer rewrites, so
    their ids are already canonical.
    """
    ids: Set[str] = set()
    for fg in groups:
        for field in fg.fields:
            if field.id:
                ids.add(field.id)
    return ids


# ============================================================
# CO125 validator
# ============================================================


class IsAuthProfileHasEngineValidator(ConnectorsValidator[ContentTypes]):
    """CO125 - the engine params (``engine_mode``, ``engine``,
    ``engine_group``) MUST be present.

    - **Grouped** connector: every ``ConnectionProfile`` must expose the
      triplet inside its own ``configurations[].fields`` (resolved
      through the owning XSOAR handler's ``serializer.yaml`` rewrites).
    - **Standard** connector: the triplet must be exposed once, at
      ``connection.general_configurations[].configurations[].fields``.

    ``engine_group`` accepts either ``engine_group`` or ``engineGroup``
    spelling.

    Skip guards:
    - **Appendix G**: connectors whose XSOAR handlers resolve to an
      integration on the engine/proxy exclusion list (EDL, TAXII Server,
      Simple API Proxy, etc.) are skipped. CO127 separately verifies
      those integrations emit NO engine params.
    - No ``connector.connection`` (missing/broken connection.yaml) - skip.
    - Grouped-only ownership skip is inherited from CO111 (grouped =
      XSOAR-only).
    """

    error_code = "CO125"
    description = (
        "Every auth profile in a connection.yaml must expose the engine "
        "triplet (engine_mode, engine, engine_group). For grouped "
        "connectors the triplet is checked per profile (using the owning "
        "handler's serializer.yaml to resolve namespaced ids like "
        "'plain_qualys_fim_engine_mode' back to 'engine_mode'); for "
        "standard connectors it is checked once at general_configurations. "
        "Integrations on the Appendix G engine/proxy exclusion list are "
        "skipped."
    )
    rationale = (
        "The engine picker (engine_mode/engine/engine_group) is how the "
        "customer routes an integration through a chosen XSOAR engine at "
        "runtime. A missing engine control means the integration can only "
        "run on the default engine - blocking on-prem and privacy-"
        "constrained deployments. CO127 handles the small set of "
        "integrations that legitimately cannot have engines."
    )
    error_message = (
        "Connector '{connector_id}' {location}: missing engine params "
        "(need '{engine_mode}', '{engine}', '{engine_group}'). Missing: "
        "{missing}."
    )
    related_field = "connection.profiles / connection.general_configurations"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CONNECTION]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @classmethod
    def _missing_engine_ids(cls, present_ids: Set[str]) -> List[str]:
        """Return the ordered list of engine ids that are absent from
        ``present_ids``. ``engine_group`` accepts both spellings."""
        missing: List[str] = []
        if ENGINE_MODE_ID not in present_ids:
            missing.append(ENGINE_MODE_ID)
        if ENGINE_ID not in present_ids:
            missing.append(ENGINE_ID)
        if not (present_ids & ENGINE_GROUP_IDS):
            missing.append("engine_group")
        return missing

    def _format_error(
        self,
        connector: Connector,
        location: str,
        missing: List[str],
    ) -> str:
        return self.error_message.format(
            connector_id=connector.object_id,
            location=location,
            engine_mode=ENGINE_MODE_ID,
            engine=ENGINE_ID,
            engine_group="engine_group",
            missing=", ".join(repr(m) for m in missing),
        )

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            connection = connector.connection
            if connection is None:
                continue

            # Appendix G exclusion: connectors whose XSOAR handlers
            # resolve to an engine/proxy-excluded integration are
            # skipped. CO127 separately verifies those integrations emit
            # NO engine params.
            if connector_is_appendix_g(connector):
                continue

            path = (
                connector.connection_file.file_path
                if connector.connection_file
                else connector.path
            )

            is_grouped = bool(connector.settings and connector.settings.grouped)

            if is_grouped:
                # Grouped: per-profile check with serializer resolution.
                for profile in connection.profiles:
                    present = profile_serialized_field_ids(connector, profile)
                    missing = self._missing_engine_ids(present)
                    if missing:
                        results.append(
                            ValidationResult(
                                validator=self,
                                message=self._format_error(
                                    connector,
                                    f"profile '{profile.id}'",
                                    missing,
                                ),
                                content_object=connector,
                                path=path,
                            )
                        )
            else:
                # Standard: single general_configurations check.
                gc: GeneralConfigurations | None = connection.general_configurations
                gc_field_groups = gc.configurations if gc else []
                present = general_config_field_ids(gc_field_groups)
                missing = self._missing_engine_ids(present)
                if missing:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self._format_error(
                                connector,
                                "general_configurations",
                                missing,
                            ),
                            content_object=connector,
                            path=path,
                        )
                    )

        return results
