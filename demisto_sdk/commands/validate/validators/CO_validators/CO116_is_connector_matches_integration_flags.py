from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Connector


# --------------------------------------------------------------------------- #
# Mapping tables — copied from the canonical migration mapper
# ``connectus/connectus_migration/connector_param_mapper.py``. Keep in sync.
# --------------------------------------------------------------------------- #

# Capability slug -> required integration flag on ``integration.script``.
#
# Only the four capabilities whose creation is gated by a fetch flag in
# ``decide_capabilities()`` are validated here:
#   - ``fetch-issues``: ``script.isfetch`` (with ``isfetch:platform``
#     consulted only when the base flag is True — see Q3 semantics below).
#   - ``log-collection``: ``script.isfetchevents``.
#   - ``fetch-assets-and-vulnerabilities``: ``script.isfetchassets``.
#   - ``threat-intelligence-enrichment``: ``script.feed``.
#
# Deliberately EXCLUDED (no flag check; always passes):
#   - ``fetch-secrets``: gated by a ``isFetchCredentials`` config-param
#     instead of a script flag, and intentionally exempt per the spec.
#   - ``automation``: derived from non-fetch command presence (Rule 6 in
#     the mapper); no script flag governs it, and exempt per the spec.
CAPABILITY_FLAG_REQUIREMENTS: dict[str, str] = {
    "fetch-issues": "isfetch",
    "log-collection": "isfetchevents",
    "fetch-assets-and-vulnerabilities": "isfetchassets",
    "threat-intelligence-enrichment": "feed",
}

# Long-running exemption: when an integration declares ``script.longRunning:
# true`` AND its ``commonfields.id`` is in this dict, the listed capability
# is exempt from the corresponding fetch-flag check. The dict is sourced
# verbatim from ``connector_param_mapper.INTEGRATION_TO_LONGRUNNING_CAPABILITY``
# (Rule 7), with capability names slugified to match the canonical ids the
# Connector model uses.
#
# Note: ``"automation"`` and ``"fetch-secrets"`` here are unreachable in
# practice (they aren't in CAPABILITY_FLAG_REQUIREMENTS, so they wouldn't
# trigger a mismatch in the first place). They are kept verbatim from the
# source for parity and auditability.
INTEGRATION_TO_LONGRUNNING_CAPABILITY: dict[str, str] = {
    "Akamai WAF SIEM": "log-collection",
    "AWS-SNS-Listener": "automation",
    "Kali Dog Security CertStream": "fetch-issues",
    "CommvaultSecurityIQ": "automation",
    "CrowdStrike Falcon Streaming v2": "fetch-issues",
    "EDL": "threat-intelligence-enrichment",
    "ExportIndicators": "threat-intelligence-enrichment",
    "Generic Webhook": "automation",
    "Generic Webhook (Form Data)": "automation",
    "Google Chronicle Backstory Streaming API": "fetch-issues",
    "LookoutMobileEndpointSecurity": "log-collection",
    "MattermostV2": "automation",
    "Microsoft Teams": "automation",
    "PingCastle": "fetch-issues",
    "Proofpoint Email Security Event Collector": "log-collection",
    "Publish List": "automation",
    "QRadar v3": "fetch-issues",
    "Retarus Secure Email Gateway": "log-collection",
    "Simple API Proxy": "automation",
    "SlackV3": "automation",
    "Symantec Cloud Secure Web Gateway Event Collector": "log-collection",
    "Symantec Endpoint Security": "log-collection",
    "Syslog v2": "fetch-issues",
    "TAXII2 Server": "threat-intelligence-enrichment",
    "TAXII Server": "threat-intelligence-enrichment",
    "UBIRCH": "automation",
    "Web File Repository": "automation",
    "Workday_IAM_Event_Generator": "automation",
    "WorkdaySignonEventGenerator": "automation",
    "XSOAR-Web-Server": "automation",
    "Zoom": "automation",
}


class IsConnectorMatchesIntegrationFlagsValidator(BaseValidator[ContentTypes]):
    error_code = "CO116"
    description = (
        "Validates that each XSOAR handler's declared capabilities are "
        "backed by the matching integration flags on the linked "
        "integration. Covers four capabilities: ``fetch-issues`` -> "
        "``isfetch``, ``log-collection`` -> ``isfetchevents``, "
        "``fetch-assets-and-vulnerabilities`` -> ``isfetchassets``, and "
        "``threat-intelligence-enrichment`` -> ``feed``. Capabilities "
        "``fetch-secrets`` and ``automation`` are exempt (they are not "
        "flag-gated in the canonical capability-resolution rules)."
    )
    rationale = (
        "The connector's declared capabilities tell the platform which "
        "behaviours to expose for an instance (event fetching, asset "
        "fetching, etc.). If the linked integration doesn't actually "
        "enable the corresponding flag, the capability cannot work at "
        "runtime: the platform will route to a fetch path the integration "
        "never wired up. The ``isfetch:platform`` variant is consulted "
        "only when the base ``isfetch`` flag is True (mirroring the "
        "mapper's Rule 3 semantics — the ``:platform`` override can "
        "*disable* but cannot *enable* a fetch). Long-running integrations "
        "(``script.longRunning: true``) are exempt for the specific "
        "capability listed in INTEGRATION_TO_LONGRUNNING_CAPABILITY, "
        "because Rule 7 deliberately routes them there regardless of "
        "fetch flags."
    )
    error_message = (
        "Connector '{connector_id}', handler '{handler_id}' (integration "
        "'{integration_id}'): the following capabilities are declared "
        "but the integration does not enable the corresponding "
        "flag.\n{mismatch_details}"
    )
    related_field = "capabilities"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Per-handler check: for every capability declared in
        ``handler.capabilities`` whose slug appears in
        ``CAPABILITY_FLAG_REQUIREMENTS``, verify that the matched
        integration's ``script`` actually enables the corresponding flag.

        Trigger gate: only XSOAR-supported handlers with a resolved
        ``related_integration`` are checked. Handlers missing an
        integration are CO100's concern.

        Q3 semantics (platform variant): the ``:platform`` variant is
        consulted ONLY when the base flag is True. If base is True AND
        ``:platform`` is explicitly False -> the capability fails (the
        platform disabled the fetch). If base is False -> the capability
        fails without consulting ``:platform`` (you cannot enable on
        platform if the base is off). Only ``fetch-issues`` /
        ``isfetch`` has this variant in practice.

        Q2 semantics (long-running exemption, NARROW): a per-capability
        mismatch is forgiven IFF the integration has
        ``script.longRunning: true`` AND the specific capability matches
        the entry in ``INTEGRATION_TO_LONGRUNNING_CAPABILITY``. Other
        capabilities on the same handler are still validated normally.

        Output: one ValidationResult per (handler) with all unforgiven
        mismatches grouped in a single message. Multiple handlers ->
        multiple results (mirrors the CO112 pattern).
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.xsoar_handlers:
                integration = handler.related_integration
                if integration is None:
                    # CO100 handles missing-integration cases.
                    continue

                script = self._get_integration_script(integration)
                integration_id = getattr(integration, "object_id", "") or ""
                is_long_running = bool(script.get("longRunning") is True)
                long_running_cap = INTEGRATION_TO_LONGRUNNING_CAPABILITY.get(
                    integration_id, ""
                )

                # Collect every top-level capability id declared by this
                # handler (sub-capabilities inherit gating from their
                # parent, so we don't re-check them).
                declared_cap_ids = {cap.id for cap in handler.capabilities}

                mismatches: List[str] = []
                for cap_id in sorted(declared_cap_ids):
                    required_flag = CAPABILITY_FLAG_REQUIREMENTS.get(cap_id)
                    if required_flag is None:
                        # Capability not in the gated set
                        # (fetch-secrets / automation / unknown) -> pass.
                        continue

                    if self._capability_flag_satisfied(script, required_flag):
                        continue

                    # Mismatch — check Q2 narrow long-running exemption.
                    if is_long_running and long_running_cap == cap_id:
                        continue

                    mismatches.append(
                        f"  capability '{cap_id}' requires integration "
                        f"flag 'script.{required_flag}: true' but it is "
                        f"not enabled"
                    )

                if not mismatches:
                    continue

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            handler_id=handler.id,
                            integration_id=integration_id,
                            mismatch_details="\n".join(mismatches),
                        ),
                        content_object=connector,
                    )
                )

        return results

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _get_integration_script(integration) -> dict:
        """Return the integration's ``script`` block as a dict.

        The Integration model exposes ``script`` either as a parsed
        sub-model or as a raw dict depending on construction path. We
        coerce to dict for uniform key access (``isfetch``, ``feed``,
        ``isfetchevents``, ``isfetchassets``, ``longRunning``, and the
        platform variants like ``isfetch:platform``).
        """
        # Prefer a raw dict if the integration carries one (test path
        # often sets a Mock with a dict attribute).
        raw = getattr(integration, "script", None)
        if isinstance(raw, dict):
            return raw

        # Pydantic model path — build a dict from the known fields the
        # validator cares about. Using getattr defensively in case the
        # model variant doesn't expose every field.
        if raw is None:
            return {}

        result: dict = {}
        for key in (
            "isfetch",
            "isfetchevents",
            "isfetchassets",
            "feed",
            "longRunning",
        ):
            value = getattr(raw, key, None)
            if value is not None:
                result[key] = value
        # Platform variants are stored under aliased keys; the parser
        # usually exposes them via a separate attribute name. Best-effort
        # lookup — if not present, the validator treats them as absent.
        for key in ("isfetch:platform",):
            # Try attribute access via the raw key (rare) and a sanitized
            # variant the model might use.
            value = getattr(raw, key, None)
            if value is None:
                value = getattr(raw, key.replace(":", "_"), None)
            if value is not None:
                result[key] = value
        return result

    @staticmethod
    def _capability_flag_satisfied(script: dict, required_flag: str) -> bool:
        """Check whether ``script[required_flag]`` is True with the
        platform-variant rules applied.

        Rules (mirror the mapper's Rule 3 semantics for ``isfetch``):
          - If base flag is not True -> NOT satisfied (platform variant
            cannot enable a fetch the base flag has disabled).
          - If base flag IS True and the ``<flag>:platform`` variant is
            explicitly False -> NOT satisfied (the platform explicitly
            disabled the capability).
          - If base flag IS True and the platform variant is absent /
            True -> satisfied.
        """
        base_value = script.get(required_flag)
        if base_value is not True:
            return False
        platform_key = f"{required_flag}:platform"
        platform_value = script.get(platform_key)
        if platform_value is False:
            return False
        return True
