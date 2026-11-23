from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import (
    ConnectionProfile,
    Connector,
    ConnectorField,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO126_is_valid_engine_params import (
    _resolver_for_profile,
)

ContentTypes = Connector

# Non-auth params must publish to the running integration - except for
# 'engine_mode', which is a UI-only field controlling the engine picker
# rather than an integration parameter.
_PUBLISH_EXEMPT_IDS = {"engine_mode"}


class IsProfileFieldsCoveredValidator(ConnectorsValidator[ContentTypes]):
    """CO123 - every non-auth field on an auth profile must publish to the
    running integration (``metadata.event.publish == true``), except
    ``engine_mode`` which is a UI-only field.

    "Auth" fields are those whose ``metadata.auth.parameter`` is set - they
    are consumed by the auth flow rather than published as integration
    params. Any other field on the profile (log-level, host, port, event
    filters, etc.) is a runtime integration param and MUST be published to
    the platform, otherwise the value the user types is silently dropped.

    Skip guard: profiles referenced ONLY by non-XSOAR handlers are skipped
    (same pattern as CO121 sub-rules C/D) - we only enforce structural
    rules for content owned by XSOAR.
    """

    error_code = "CO123"
    description = (
        "For every auth profile that is referenced by at least one XSOAR "
        "handler, verify that every non-auth field on the profile has "
        "metadata.event.publish == true. 'engine_mode' is exempt."
    )
    rationale = (
        "Non-auth fields on a profile map 1:1 to runtime integration "
        "parameters. Without event.publish=true the value the user types "
        "into the connection form never reaches the integration - a silent "
        "misconfiguration only discoverable at fetch/run time."
    )
    error_message = (
        "Connector '{connector_id}' profile '{profile_id}' field "
        "'{field_id}' must set metadata.event.publish = true "
        "(non-auth fields on an auth profile are required to publish)."
    )
    related_field = "connection.profiles.configurations.fields.metadata.event.publish"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CONNECTION]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_auth_field(field: ConnectorField) -> bool:
        """A field is an "auth field" iff its metadata declares an
        ``auth.parameter`` mapping - i.e. it's part of the auth form, not
        a regular runtime integration param.
        """
        meta = field.metadata or {}
        auth = meta.get("auth") if isinstance(meta, dict) else None
        if not isinstance(auth, dict):
            return False
        return "parameter" in auth

    @staticmethod
    def _is_published(field: ConnectorField) -> bool:
        meta = field.metadata or {}
        event = meta.get("event") if isinstance(meta, dict) else None
        if not isinstance(event, dict):
            return False
        return event.get("publish") is True

    @staticmethod
    def _iter_profile_fields(profile: ConnectionProfile) -> Iterable[ConnectorField]:
        """Yield every field on the profile (across all FieldGroup rows in
        ``configurations``)."""
        for fg in profile.configurations:
            for field in fg.fields:
                yield field

    @staticmethod
    def _has_xsoar_reference(connector: Connector, profile_id: str) -> bool:
        """Return True iff at least one XSOAR handler references the
        profile via ``handler.capabilities[*].auth_options[*].id``."""
        for h in connector.handlers:
            if not h.is_xsoar:
                continue
            for cap in h.capabilities:
                if any(opt.id == profile_id for opt in cap.auth_options):
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
            connection = connector.connection
            if connection is None:
                continue

            path = (
                connector.connection_file.file_path
                if connector.connection_file
                else connector.path
            )

            for profile in connection.profiles:
                # Ownership skip: only enforce for profiles at least one
                # XSOAR handler cares about.
                if not self._has_xsoar_reference(connector, profile.id):
                    continue

                # Build {raw_id -> canonical_id} from serializer rewrites
                # so exemption checks (e.g. ``engine_mode``) work for
                # grouped connectors whose ids are namespaced
                # (e.g. ``plain_circl_engine_mode``).
                resolver = _resolver_for_profile(connector, profile.id)

                for field in self._iter_profile_fields(profile):
                    # Skip auth fields (they never publish - CO121 owns
                    # their .auth.parameter contract).
                    if self._is_auth_field(field):
                        continue
                    # Skip the single documented exemption (resolve
                    # namespaced ids via the serializer first).
                    canonical_id = resolver.get(field.id, field.id)
                    if canonical_id in _PUBLISH_EXEMPT_IDS:
                        continue
                    if not self._is_published(field):
                        results.append(
                            ValidationResult(
                                validator=self,
                                message=self.error_message.format(
                                    connector_id=connector.object_id,
                                    profile_id=profile.id,
                                    field_id=field.id,
                                ),
                                content_object=connector,
                                path=path,
                            )
                        )

        return results


# Re-export a couple of helper names so future validators (CO124-CO128)
# can reuse the same auth-vs-non-auth distinction without duplicating.
__all__ = [
    "IsProfileFieldsCoveredValidator",
    "_PUBLISH_EXEMPT_IDS",
]
