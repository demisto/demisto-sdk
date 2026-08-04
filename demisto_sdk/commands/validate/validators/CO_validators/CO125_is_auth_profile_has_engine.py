from __future__ import annotations

from typing import Iterable, List, Set

from demisto_sdk.commands.content_graph.objects.connector import (
    ConnectionProfile,
    Connector,
    ConnectorField,
    FieldGroup,
    GeneralConfigurations,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.CO_validators._engine_appendix import (
    ENGINE_GROUP_IDS,
    ENGINE_ID,
    ENGINE_MODE_ID,
    connector_is_appendix_g,
)

ContentTypes = Connector

# The engine triplet a proper engine picker must expose.
_REQUIRED_ENGINE_IDS: Set[str] = {ENGINE_MODE_ID, ENGINE_ID}
# For engine_group we accept either the snake_case or camelCase spelling.


class IsAuthProfileHasEngineValidator(ConnectorsValidator[ContentTypes]):
    """CO125 - the engine params (``engine_mode``, ``engine``,
    ``engine_group``) MUST be present.

    - **Grouped** connector: every ``ConnectionProfile`` must expose the
      triplet inside its own ``configurations[].fields`` block.
    - **Standard** connector: the triplet must be exposed once, at
      ``connection.general_configurations[].configurations[].fields``.

    ``engine_group`` accepts either ``engine_group`` or ``engineGroup``
    spelling.

    Skip guards:
    - **Appendix G**: connectors whose XSOAR handlers resolve to an
      integration on the engine/proxy exclusion list (EDL, TAXII Server,
      Simple API Proxy, etc. - full list in ``_engine_appendix.py``)
      are skipped. CO127 separately verifies those integrations emit NO
      engine params.
    - No ``connector.connection`` (missing/broken connection.yaml) - skip.
    - Grouped-only ownership skip is inherited from CO111 (grouped =
      XSOAR-only).
    """

    error_code = "CO125"
    description = (
        "Every auth profile in a connection.yaml must expose the engine "
        "triplet (engine_mode, engine, engine_group). For grouped "
        "connectors the triplet is checked per profile; for standard "
        "connectors it is checked once at general_configurations. "
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

    @staticmethod
    def _field_ids_in_groups(groups: Iterable[FieldGroup]) -> Set[str]:
        ids: Set[str] = set()
        for fg in groups:
            for field in fg.fields:
                if field.id:
                    ids.add(field.id)
        return ids

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

            # Appendix G exclusion: connectors whose XSOAR handlers resolve
            # to an engine/proxy-excluded integration are skipped. CO127
            # separately verifies those integrations emit NO engine params.
            if connector_is_appendix_g(connector):
                continue

            path = (
                connector.connection_file.file_path
                if connector.connection_file
                else connector.path
            )

            is_grouped = bool(
                connector.settings and connector.settings.grouped
            )

            if is_grouped:
                # Grouped: per-profile check.
                for profile in connection.profiles:
                    missing = self._missing_engine_ids(
                        self._field_ids_in_groups(profile.configurations)
                    )
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
                missing = self._missing_engine_ids(
                    self._field_ids_in_groups(gc_field_groups)
                )
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
