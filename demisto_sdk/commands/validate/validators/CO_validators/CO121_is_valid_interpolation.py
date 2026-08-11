from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from demisto_sdk.commands.content_graph.objects.connector import (
    ConnectionProfile,
    Connector,
    ConnectorField,
    HandlerData,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO120_is_proxy_and_insecure_exists import (
    INSECURE_ALIASES,
    PROXY_ALIASES,
)

ContentTypes = Connector

# §2.6.2: LEFT keys in interpolation_mapping must be auth-field parameter
# names on the profile - never engine/proxy/insecure and their aliases.
_ENGINE_RESERVED: Set[str] = {"engine", "engine_group", "engineGroup", "engine_mode"}
_RESERVED_LEFT_KEYS: Set[str] = _ENGINE_RESERVED | PROXY_ALIASES | INSECURE_ALIASES

# Suffix strippers - only allowed for XSOAR credentials (type-9) params.
_CREDENTIALS_SUFFIXES: Tuple[str, ...] = (
    ".identifier",
    ".password",
    ".credentials.sshkey",
)

# XSOAR ParameterType.AUTH = 9 (see demisto_sdk.commands.common.constants).
_CREDENTIALS_PARAM_TYPE = 9


class IsValidInterpolationValidator(ConnectorsValidator[ContentTypes]):
    """CO121 - interpolation_mapping on a ConnectionProfile must satisfy:

    A. LEFT (auth-field name) exists in the profile - either as
       ``fields[*].id`` OR as ``fields[*].metadata.auth.parameter``
       ("serialized or deserialized").
    B. LEFT must NOT be a general/reserved param
       (proxy/insecure/engine/engine_group/engine_mode + their aliases,
       per §2.6.2).
    C. RIGHT (integration param name), after stripping trailing
       ``.identifier`` / ``.password`` / ``.credentials.sshkey``, must exist
       as ``integration.params[*].name`` on at least one of the XSOAR
       handlers that reference this profile.
    D. The credentials-style suffix is only valid when the referenced
       integration param has ``type == 9`` (ParameterType.AUTH).
    E. LEFT must NOT target a profile field whose
       ``metadata.event.publish`` is ``true``. Publish and interpolation
       are mutually exclusive contracts: an interpolated field is
       consumed by the auth flow and must NOT also publish its raw
       pre-interpolation value to the runtime integration - the
       complement of CO123 (which requires non-interpolated fields to
       publish).

    Skip guards:
    - Skip profiles that are not interpolated (``metadata.xsoar
      .interpolated != true`` OR no ``interpolation_mapping``).
    - Sub-rules A/B/E are intrinsic to the profile and always run.
    - Sub-rules C/D need ``handler.related_integration``. If NO XSOAR
      handler references the profile (or none of them has a resolved
      integration), C/D are skipped for that profile - CO114/CO120 already
      flag unresolved-integration handlers.
    - Non-XSOAR handlers do NOT participate in the C/D integration lookup.
    - Sub-rule E is skipped when Sub-rule B already fires for the same
      LEFT (a reserved LEFT is a harder failure; suppressing E avoids
      double-reporting on the same pair).
    """

    error_code = "CO121"
    description = (
        "Validates each interpolated auth profile's interpolation_mapping: "
        "left keys must be auth-field parameter names present in the "
        "profile (never engine/engine_group/proxy/insecure) and must not "
        "target a field with metadata.event.publish=true (publish and "
        "interpolation are mutually exclusive); right values must exist "
        "as parameter names on the backing integration, and credentials-"
        "suffix syntax (.identifier / .password) is only valid for "
        "integration params of type 9 (credentials)."
    )
    rationale = (
        "interpolation_mapping is the contract between the connector's "
        "user-facing auth fields and the runtime integration params. A "
        "broken mapping (missing left auth field, mistyped right param, "
        "wrong .identifier/.password on a non-credentials param, or a "
        "left key that also publishes to the integration) is a runtime "
        "auth failure the customer only discovers at fetch time."
    )
    error_message = "Connector '{connector_id}' profile '{profile_id}': {details}."
    related_field = "connection.profiles.metadata.xsoar.interpolation_mapping"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CONNECTION]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_interpolated(profile: ConnectionProfile) -> bool:
        meta = profile.metadata or {}
        xsoar = meta.get("xsoar") if isinstance(meta, dict) else None
        if not isinstance(xsoar, dict):
            return False
        return xsoar.get("interpolated") is True

    @staticmethod
    def _interpolation_mapping(profile: ConnectionProfile) -> Optional[str]:
        meta = profile.metadata or {}
        xsoar = meta.get("xsoar") if isinstance(meta, dict) else None
        if not isinstance(xsoar, dict):
            return None
        return xsoar.get("interpolation_mapping")

    @staticmethod
    def _iter_profile_field_names(profile: ConnectionProfile) -> Iterable[str]:
        """Yield BOTH the raw ``field.id`` AND the field's
        ``metadata.auth.parameter`` (when present) - LEFT lookup accepts
        either form.
        """
        for fg in profile.configurations:
            for field in fg.fields:
                yield field.id
                meta = field.metadata or {}
                auth = meta.get("auth") if isinstance(meta, dict) else None
                if isinstance(auth, dict):
                    param = auth.get("parameter")
                    if param:
                        yield param

    @staticmethod
    def _profile_field_index(
        profile: ConnectionProfile,
    ) -> Dict[str, ConnectorField]:
        """Return ``{lookup_name -> ConnectorField}`` keyed by BOTH the
        raw ``field.id`` AND the field's ``metadata.auth.parameter``
        (same dual-lookup semantics as
        :meth:`_iter_profile_field_names`), used by Sub-rule E to
        resolve a LEFT key back to its underlying field so we can check
        ``metadata.event.publish``.

        On the (defensive) case of a collision between id and
        auth.parameter across two different fields, first write wins -
        Sub-rule A/B behavior for that name is unchanged, and Sub-rule E
        is a best-effort publish check that only fires when the LEFT
        resolves cleanly.
        """
        index: Dict[str, ConnectorField] = {}
        for fg in profile.configurations:
            for field in fg.fields:
                index.setdefault(field.id, field)
                meta = field.metadata or {}
                auth = meta.get("auth") if isinstance(meta, dict) else None
                if isinstance(auth, dict):
                    param = auth.get("parameter")
                    if param:
                        index.setdefault(param, field)
        return index

    @staticmethod
    def _is_published(field: ConnectorField) -> bool:
        """Mirror of CO123's publish detection: a field is "published"
        iff ``metadata.event.publish is True``. Missing metadata / event
        block / publish key all mean False.
        """
        meta = field.metadata or {}
        event = meta.get("event") if isinstance(meta, dict) else None
        if not isinstance(event, dict):
            return False
        return event.get("publish") is True

    @staticmethod
    def _parse_pairs(mapping: str) -> List[Tuple[str, str]]:
        """Parse ``left:right,left:right,...`` into a list of tuples. A
        malformed pair (no colon) is returned as ``(left, "")`` so
        Sub-rule A / RIGHT-empty can flag it consistently.
        """
        pairs: List[Tuple[str, str]] = []
        for raw in (mapping or "").split(","):
            token = raw.strip()
            if not token:
                continue
            if ":" in token:
                left, right = token.split(":", 1)
                pairs.append((left.strip(), right.strip()))
            else:
                pairs.append((token, ""))
        return pairs

    @staticmethod
    def _strip_credentials_suffix(right: str) -> Tuple[str, Optional[str]]:
        """Return ``(base, suffix)``; ``suffix`` is None when no
        credentials-style suffix was found.
        """
        for suffix in _CREDENTIALS_SUFFIXES:
            if right.endswith(suffix):
                return right[: -len(suffix)], suffix
        return right, None

    @staticmethod
    def _xsoar_handlers_for_profile(
        connector: Connector, profile_id: str
    ) -> List[HandlerData]:
        matches: List[HandlerData] = []
        for h in connector.handlers:
            if not h.is_xsoar:
                continue
            for cap in h.capabilities:
                if any(opt.id == profile_id for opt in cap.auth_options):
                    matches.append(h)
                    break
        return matches

    @staticmethod
    def _find_integration_param(handler: HandlerData, name: str) -> Optional[Any]:
        integration = handler.related_integration
        if integration is None:
            return None
        params = getattr(integration, "params", None) or []
        for p in params:
            if getattr(p, "name", None) == name:
                return p
        return None

    # ------------------------------------------------------------------
    # Main entry point
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
                if not self._is_interpolated(profile):
                    continue
                mapping = self._interpolation_mapping(profile)
                if not mapping:
                    continue

                profile_field_names = set(self._iter_profile_field_names(profile))
                # Parallel index used by Sub-rule E to resolve LEFT -> field
                # for the publish check. Keeping this separate from
                # ``profile_field_names`` preserves Sub-rule A's set-membership
                # semantics and avoids touching call sites unrelated to E.
                profile_field_index = self._profile_field_index(profile)
                xsoar_handlers = self._xsoar_handlers_for_profile(connector, profile.id)
                resolved_xsoar_handlers = [
                    h for h in xsoar_handlers if h.related_integration is not None
                ]

                for left, right in self._parse_pairs(mapping):
                    for detail in self._check_pair(
                        left,
                        right,
                        profile_field_names,
                        profile_field_index,
                        resolved_xsoar_handlers,
                    ):
                        results.append(
                            ValidationResult(
                                validator=self,
                                message=self.error_message.format(
                                    connector_id=connector.object_id,
                                    profile_id=profile.id,
                                    details=detail,
                                ),
                                content_object=connector,
                                path=path,
                            )
                        )

        return results

    # ------------------------------------------------------------------
    # Per-pair rule checks
    # ------------------------------------------------------------------

    def _check_pair(
        self,
        left: str,
        right: str,
        profile_field_names: Set[str],
        profile_field_index: Dict[str, ConnectorField],
        resolved_xsoar_handlers: List[HandlerData],
    ) -> List[str]:
        details: List[str] = []

        # Sub-rule B: LEFT must not be a reserved general param.
        if left in _RESERVED_LEFT_KEYS:
            details.append(
                f"LEFT '{left}' is a reserved general param and cannot "
                f"appear on the LEFT of interpolation_mapping"
            )
        # Sub-rule A: LEFT must exist in the profile.
        elif left not in profile_field_names:
            details.append(
                f"LEFT '{left}' does not match any field id or "
                f"metadata.auth.parameter on the profile"
            )
        else:
            # Sub-rule E: LEFT resolved to a real profile field. That
            # field must NOT publish to the runtime integration -
            # interpolation and publish are mutually exclusive (an
            # interpolated field is consumed by the auth flow; if it
            # also published, the raw pre-interpolation value would
            # leak through as an integration param). Complements CO123
            # which enforces the non-interpolated => publish=true
            # direction.
            field = profile_field_index.get(left)
            if field is not None and self._is_published(field):
                details.append(
                    f"LEFT '{left}' targets a profile field with "
                    f"metadata.event.publish=true; publish and "
                    f"interpolation are mutually exclusive - remove the "
                    f"field from interpolation_mapping or set publish=false"
                )

        # Sub-rule C/D: check RIGHT against the integration - only if we
        # have at least one XSOAR handler with a resolved integration for
        # this profile.
        if not right:
            details.append(
                f"RIGHT for LEFT '{left}' is empty (missing ':' in the "
                f"interpolation_mapping pair)"
            )
        elif resolved_xsoar_handlers:
            base, suffix = self._strip_credentials_suffix(right)
            # Sub-rule C: base name must exist on at least one integration.
            match = None
            for h in resolved_xsoar_handlers:
                p = self._find_integration_param(h, base)
                if p is not None:
                    match = p
                    break
            if match is None:
                details.append(
                    f"RIGHT base '{base}' is not declared on the backing "
                    f"integration params of any XSOAR handler"
                )
            elif suffix is not None:
                # Sub-rule D: credentials suffix only valid for type-9 params.
                param_type = getattr(match, "type", None)
                if param_type != _CREDENTIALS_PARAM_TYPE:
                    details.append(
                        f"credentials suffix '{suffix}' on RIGHT '{right}' "
                        f"is only valid for integration params of "
                        f"type=9 (credentials); '{base}' has type="
                        f"{param_type}"
                    )

        return details
