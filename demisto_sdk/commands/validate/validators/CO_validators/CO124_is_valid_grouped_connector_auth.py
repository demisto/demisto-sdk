from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import (
    ConnectionProfile,
    Connector,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsValidGroupedConnectorAuthValidator(ConnectorsValidator[ContentTypes]):
    """CO124 - grouped-only. Every profile in a grouped connector that
    carries an auth surface MUST declare a non-empty
    ``metadata.xsoar.interpolation_mapping`` string.

    Grouped connectors expose per-integration auth via multiple tiles
    (view_groups). Each profile's runtime auth mapping is derived from
    ``metadata.xsoar.interpolation_mapping`` (LEFT: auth-field name,
    RIGHT: integration param). Without a mapping the platform doesn't
    know how to hand user input to the integration - authentication
    silently breaks at fetch time.

    A present-but-empty ``interpolation_mapping: ""`` COUNTS as missing
    (a valid mapping needs at least one ``left:right`` pair).

    Skip guards:
    - Sub-rule A: Non-grouped connector - skip entirely.
    - Sub-rule B: Profile has no auth surface - skip. A profile that
      exposes ONLY framework fields (proxy / insecure / engine /
      engine_mode / engineGroup / a fixed URL) and no ``vault_mappings``
      has nothing to interpolate; requiring a mapping there would force
      an empty ``""`` value that CO121 would immediately reject as
      malformed. Legitimate examples: passthrough profiles for public
      intel feeds (nmap, whois, dnstwist, tor-exit-addresses, spamhaus,
      ...) and ``external_auth`` "No Authentication Required" tiles
      (dbot_truth_bombs, sample_incident_generator, zoom_feed, ...).
      An auth surface exists when the profile declares at least one
      ``field.metadata.auth.parameter`` OR at least one
      ``vault_mappings`` entry.

    Ownership note:
    - No per-profile ownership check needed. Grouped connectors are
      XSOAR-only by design (enforced by CO111
      ``GroupedConnectorXSOAROnlyCapabilities``), so every profile in a
      grouped connector is XSOAR-relevant.

    Complements:
    - CO121 ``IsValidInterpolation`` validates the CONTENTS of the
      mapping when it exists; CO124 ensures the mapping is ALWAYS present
      on grouped-connector profiles that actually carry auth fields.
    """

    error_code = "CO124"
    description = (
        "Grouped-only. Every ConnectionProfile in a grouped connector "
        "that carries an auth surface (any field.metadata.auth.parameter "
        "or any vault_mappings entry) must declare "
        "metadata.xsoar.interpolation_mapping (non-empty string). "
        "Profiles with no auth surface are skipped - they have nothing "
        "to interpolate. Grouped connectors are XSOAR-only by CO111, so "
        "no per-profile ownership check is applied."
    )
    rationale = (
        "Grouped connectors depend on interpolation_mapping to route the "
        "user's auth-form input to the correct runtime integration "
        "parameter. A missing or empty mapping means the platform can't "
        "wire the auth form to the integration - authentication silently "
        "fails at fetch time."
    )
    error_message = (
        "Grouped connector '{connector_id}' profile '{profile_id}': " "{detail}."
    )
    related_field = "connection.profiles.metadata.xsoar.interpolation_mapping"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CONNECTION]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _interpolation_mapping(profile: ConnectionProfile) -> object:
        """Return the raw ``metadata.xsoar.interpolation_mapping`` value
        (or None if the path doesn't exist).
        """
        meta = profile.metadata or {}
        if not isinstance(meta, dict):
            return None
        xsoar = meta.get("xsoar")
        if not isinstance(xsoar, dict):
            return None
        return xsoar.get("interpolation_mapping")

    @staticmethod
    def _has_auth_surface(profile: ConnectionProfile) -> bool:
        """Return True iff the profile carries at least one user-supplied
        auth input that would need to be interpolated into an integration
        param.

        An auth surface is detected via:
        - Any ``field.metadata.auth.parameter`` on any configuration
          field (matches CO121's LEFT-lookup logic), OR
        - Any ``vault_mappings`` entry (passthrough profiles that draw
          credentials from a vault still need a mapping).

        Profiles exposing ONLY framework fields (proxy / insecure /
        engine* / a fixed URL) have no auth surface and therefore no
        mapping to declare.
        """
        if profile.vault_mappings:
            return True
        for fg in profile.configurations:
            for field in fg.fields:
                meta = field.metadata or {}
                if not isinstance(meta, dict):
                    continue
                auth = meta.get("auth")
                if isinstance(auth, dict) and auth.get("parameter"):
                    return True
        return False

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            # Sub-rule A: grouped-only short-circuit.
            if not (connector.settings and connector.settings.grouped):
                continue

            connection = connector.connection
            if connection is None:
                continue

            path = (
                connector.connection_file.file_path
                if connector.connection_file
                else connector.path
            )

            for profile in connection.profiles:
                # Sub-rule B: no auth surface -> nothing to interpolate.
                if not self._has_auth_surface(profile):
                    continue

                mapping = self._interpolation_mapping(profile)

                # A valid mapping is a non-empty STRING. Missing key,
                # None, empty string, or a non-string all fail with a
                # single unified error message.
                if isinstance(mapping, str) and mapping.strip():
                    continue

                if mapping is None:
                    detail = "metadata.xsoar.interpolation_mapping is missing"
                elif isinstance(mapping, str):
                    detail = (
                        "metadata.xsoar.interpolation_mapping is empty "
                        "(must be a non-empty 'left:right,...' string)"
                    )
                else:
                    detail = (
                        f"metadata.xsoar.interpolation_mapping must be a "
                        f"non-empty string, got "
                        f"{type(mapping).__name__}"
                    )

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            profile_id=profile.id,
                            detail=detail,
                        ),
                        content_object=connector,
                        path=path,
                    )
                )

        return results
